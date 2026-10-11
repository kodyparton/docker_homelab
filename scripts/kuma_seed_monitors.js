/* Seeds Uptime Kuma with one HTTP monitor per public DNS name in this stack.
 *
 * Runs INSIDE the uptime-kuma container (`docker exec`), because Kuma 1.x has
 * no REST API for monitor CRUD -- everything goes over Socket.IO -- and the
 * container already ships `socket.io-client`. That means no new dependency is
 * installed anywhere on the host to make this work.
 *
 * The password is read from the KUMA_PASSWORD environment variable, never from
 * argv, so it does not show up in `ps` output for other users on the box.
 *
 * Idempotent: monitors are matched by name against what already exists, so a
 * second run adds only what is missing and never creates duplicates.
 */
const { io } = require("socket.io-client");

const USERNAME = process.env.KUMA_USERNAME || "kparton";
const PASSWORD = process.env.KUMA_PASSWORD || "";
const TOTP = process.env.KUMA_TOTP || "";
const MAKE_STATUS_PAGE = process.env.KUMA_STATUS_PAGE !== "0";
const STATUS_SLUG = process.env.KUMA_STATUS_SLUG || "default";
const DRY_RUN = process.env.DRY_RUN === "1";

// hostname -> friendly name. Kept explicit rather than derived from the
// subdomain, so the Kuma list reads like the Homepage dashboard does.
const SERVICES = [
  ["sonarr.kodyparton.com",     "Sonarr"],
  ["sonarr4k.kodyparton.com",   "Sonarr 4K"],
  ["radarr.kodyparton.com",     "Radarr"],
  ["radarr4k.kodyparton.com",   "Radarr 4K"],
  ["prowlarr.kodyparton.com",   "Prowlarr"],
  ["request.kodyparton.com",    "Seerr"],
  ["tautulli.kodyparton.com",   "Tautulli"],
  ["downloads.kodyparton.com",  "qBittorrent"],
  ["huntarr.kodyparton.com",    "Huntarr"],
  ["audiobooks.kodyparton.com", "Audiobookshelf"],
  ["books.kodyparton.com",      "LazyLibrarian"],
  ["comics.kodyparton.com",     "YACReader"],
  ["photos.kodyparton.com",     "Immich"],
  ["paperless.kodyparton.com",  "Paperless-ngx"],
  ["notes.kodyparton.com",      "Trilium"],
  ["tasks.kodyparton.com",      "Vikunja"],
  ["vault.kodyparton.com",      "Vaultwarden"],
  ["n8n.kodyparton.com",        "n8n"],
  ["auth.kodyparton.com",       "Authelia"],
  ["dns.kodyparton.com",        "AdGuard Home"],
  ["infisical.kodyparton.com",  "Infisical"],
  ["home.kodyparton.com",       "Homepage"],
  ["uptime.kodyparton.com",     "Uptime Kuma"],
  // Network appliances, not containers. These two reach hardware off the Mac
  // Mini via NPM's only https upstreams; a failure here means the appliance or
  // the proxy, not a container. See docs/containers/nginx-proxy-manager.md.
  ["nas.kodyparton.com",        "UNAS Pro"],
  ["ziggo.kodyparton.com",      "Ziggo Modem"],
];

function monitorFor(hostname, name) {
  return {
    type: "http",
    name,
    url: `https://${hostname}`,
    method: "GET",
    interval: 60,
    retryInterval: 60,
    resendInterval: 0,
    maxretries: 2,
    timeout: 48,
    // 200-399, NOT Kuma's 200-299 default. Five of these hosts answer with a
    // redirect to a login page (books 303, dns 302, paperless 302, request 307,
    // uptime 302) -- all measured, not assumed. Under the default range those
    // five would report down forever while being perfectly healthy.
    accepted_statuscodes: ["200-399"],
    maxredirects: 10,
    // The wildcard *.kodyparton.com cert from NPM is valid and verified from
    // inside this container, so TLS verification stays ON.
    ignoreTls: false,
    upsideDown: false,
    expiryNotification: true,
    description: null,
    notificationIDList: {},
    active: true,
  };
}

const socket = io("http://localhost:3001", {
  transports: ["websocket"],
  reconnection: false,
  timeout: 20000,
});

const call = (event, ...args) =>
  new Promise((resolve, reject) => {
    const t = setTimeout(() => reject(new Error(`timeout on "${event}"`)), 30000);
    socket.emit(event, ...args, (res) => {
      clearTimeout(t);
      res && res.ok === false ? reject(new Error(res.msg || `"${event}" failed`)) : resolve(res);
    });
  });

// Kuma pushes the full monitor list as an unsolicited event after login rather
// than answering a "list monitors" request, so capture it as it arrives.
let existing = null;
socket.on("monitorList", (list) => { existing = list || {}; });

const waitFor = (pred, ms, what) =>
  new Promise((resolve, reject) => {
    const start = Date.now();
    (function poll() {
      if (pred()) return resolve();
      if (Date.now() - start > ms) return reject(new Error(`timed out waiting for ${what}`));
      setTimeout(poll, 150);
    })();
  });

(async () => {
  try {
    if (!PASSWORD) throw new Error("KUMA_PASSWORD is empty");

    await new Promise((resolve, reject) => {
      socket.on("connect", resolve);
      socket.on("connect_error", (e) => reject(new Error(`connect failed: ${e.message}`)));
    });

    const login = await call("login", { username: USERNAME, password: PASSWORD, token: TOTP });
    if (!login || !login.ok) {
      throw new Error(
        login && login.msg
          ? `login rejected: ${login.msg}`
          : "login rejected (wrong password, or 2FA is on -- set KUMA_TOTP)"
      );
    }
    console.log(`Authenticated as ${USERNAME}.`);

    await waitFor(() => existing !== null, 15000, "monitor list");
    const byName = new Map(Object.values(existing).map((m) => [m.name, m]));
    console.log(`Existing monitors: ${byName.size}`);

    const created = [];
    const skipped = [];
    for (const [hostname, name] of SERVICES) {
      if (byName.has(name)) { skipped.push(name); continue; }
      if (DRY_RUN) { created.push({ name, id: null }); continue; }
      const res = await call("add", monitorFor(hostname, name));
      created.push({ name, id: res.monitorID });
      console.log(`  + ${name.padEnd(16)} https://${hostname}`);
    }

    console.log(
      `\n${DRY_RUN ? "[DRY RUN] would create" : "Created"}: ${created.length}` +
      (skipped.length ? `   Already present (skipped): ${skipped.length}` : "")
    );

    if (MAKE_STATUS_PAGE && !DRY_RUN) {
      // Homepage's uptimekuma widget reads a PUBLIC status page, not the admin
      // API -- that is why it needs no credential. Without a status page at
      // this slug the widget renders 0 up / 0 down, which is exactly the state
      // the dashboard was left in.
      let slugExists = true;
      try {
        await call("addStatusPage", "Homelab", STATUS_SLUG);
        console.log(`\nCreated status page "/status/${STATUS_SLUG}".`);
        slugExists = false;
      } catch (e) {
        console.log(`\nStatus page "/status/${STATUS_SLUG}" already exists — updating its monitor list.`);
      }

      const all = Object.values(existing).concat(created.filter((c) => c.id));
      const monitorList = [];
      const seen = new Set();
      for (const [, name] of SERVICES) {
        const m = byName.get(name) || created.find((c) => c.name === name);
        if (m && m.id && !seen.has(m.id)) { seen.add(m.id); monitorList.push({ id: m.id }); }
      }

      await call(
        "saveStatusPage",
        STATUS_SLUG,
        {
          slug: STATUS_SLUG,
          title: "Kody's Homelab",
          description: "Live service status",
          icon: "/icon.svg",
          theme: "dark",
          published: true,
          showTags: false,
          domainNameList: [],
          customCSS: "",
          footerText: null,
          showPoweredBy: false,
          googleAnalyticsId: null,
        },
        null,
        [{ name: "Services", weight: 1, monitorList }]
      );
      console.log(`Published ${monitorList.length} monitors to /status/${STATUS_SLUG}.`);
    }

    socket.close();
    process.exit(0);
  } catch (err) {
    console.error(`\nFAILED: ${err.message}`);
    socket.close();
    process.exit(1);
  }
})();
