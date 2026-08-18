# n8n Workflows — Setup Report

Six workflows built via n8n's REST API. All currently **inactive** — activate each one (toggle top-right in the editor) once its credentials are real.

## Login
- URL: `http://localhost:5678` (or `https://n8n.kodyparton.com` once the NPM routing fix is applied)
- Email: `kody.m.parton@gmail.com`
- Password: set during provisioning — change it after first login (Settings → Personal → Change Password) if you haven't already.

## Real problems these surfaced already (worth fixing regardless of the workflows)
- **`downloads.kodyparton.com` doesn't resolve via DNS at all right now.**
- **`watchtower` is stuck in a restart loop** (`docker logs watchtower` to see why).
- **`lazylibrarian`'s container is stopped and its last backup is 25 days old** (threshold is 14).
- **`trilium`'s container exists but was never started.**
- **`audiobookshelf` has never produced a backup file**, ever — the folder exists, nothing writes to it.
- `heimdall/config/compose.yml` is essentially empty (just `services:`, no service defined) — worth fixing or removing separately.

## Shared setup (do once, covers workflows 01–03)
1. **Enable SSH**: System Settings → General → Sharing → turn on **Remote Login**, allow for user `kp-srv-01`.
2. **Fill in the `Mac Mini SSH` credential** (n8n → Settings → Credentials): created as a stub (host `host.docker.internal`, port 22, user `kp-srv-01`, placeholder password) — set the real password (or swap to a private key). All 3 workflows already point at this one credential, so fixing it once fixes all three. If `host.docker.internal` doesn't resolve, use `192.168.178.69`.
3. **Create a Discord webhook**: in your target channel → Channel Settings → Integrations → Webhooks → New Webhook → Copy Webhook URL → paste it into the **`Homelab Discord Webhook`** credential in n8n (also a stub).
4. **Activate each workflow** via the toggle top-right once its credentials are real — all 6 are currently inactive.

## 01 – Certificate & Domain Expiry Monitor
`http://localhost:5678/workflow/bjSOzvcj7irAzMu0` — daily 08:00. Checks TLS expiry on your 4 known domains + RDAP domain-registration expiry for `kodyparton.com`. Alerts ≤30/≤14/≤7 days. No extra manual steps beyond shared setup. (Live run at build time: everything's fine except `downloads.kodyparton.com`, which can't even be checked — see above.)

## 02 – Docker Drift Detection
`http://localhost:5678/workflow/BT6HWEX9LnNtePJo` — every 6h. Diffs each `compose.yml`'s declared image against the running container. No extra manual steps beyond shared setup.

## 03 – Backup Verification
`http://localhost:5678/workflow/3JHqgAwVYe4p0iw9` — daily 09:00. Checks freshness + zip/tar integrity for sonarr/radarr/sonarr-4k/radarr-4k/prowlarr/tautulli/huntarr/lazylibrarian/audiobookshelf. qBittorrent's session state was deliberately excluded (not a "backup" in the relevant sense). No extra manual steps beyond shared setup.

## 04a – Entra Joiner / 04b – Entra Leaver
`http://localhost:5678/workflow/ejCEgXD14EaV5KlM` / `http://localhost:5678/workflow/AcpyV30Q1n9LRghN`
1. Sign up a free tenant at portal.azure.com → Microsoft Entra ID.
2. Entra admin center → **App registrations → New registration** (any name, single tenant).
3. **API permissions → Add a permission → Microsoft Graph → Application permissions** → add `User.ReadWrite.All`, `Group.ReadWrite.All`, `Directory.ReadWrite.All` → **Grant admin consent**.
4. **Certificates & secrets → New client secret** → copy the value immediately.
5. Grab the **Tenant ID** and **Application (client) ID** from the app's Overview page.
6. In n8n, open credential **"Entra Graph (App-Only)"** (OAuth2, client-credentials grant) and fill in: Access Token URL `https://login.microsoftonline.com/<tenant-id>/oauth2/v2.0/token`, Client ID, Client Secret.
7. In 04a's **"Build User Payload"** Code node, replace `YOUR-TENANT` with your real `.onmicrosoft.com` or verified custom domain.
8. Activate each workflow, open its Form Trigger node, copy the **Production URL** — that's the link you'll actually use to submit joiner/leaver requests.
9. When testing, use Entra **Object IDs** (not display names) in the joiner's "Groups to assign" field.

Both flows end in a clean summary node rather than logging anywhere — no destination was specified, so wire a Notion/Sheets/Slack node onto the end if you want persistent audit logs.

## 05 – Job Application Pipeline
`http://localhost:5678/workflow/JC6zZoQM0UFoGvv8` — every 6h.
1. Free signup at developer.adzuna.com → get `app_id`/`app_key`, paste into the "Search Adzuna NL" node (currently `YOUR_ADZUNA_APP_ID`/`YOUR_ADZUNA_APP_KEY`).
2. Create a Notion integration at notion.so/my-integrations, copy the token into the **"Job Pipeline Notion"** credential.
3. Build a Notion database with these exact properties: a title property, **URL** (URL), **Company** (Text), **Location** (Text), **Score** (Number), **Posted Date** (Date), **Status** (Select, with a "New" option). Share the database with your integration.
4. Paste the database ID (32-char hex from its URL) into `YOUR_NOTION_DATABASE_ID` in both Notion nodes.
5. Edit the **"Search Config"** Set node — `searchTerms` and `keywordWeights` are placeholder examples, tune to your actual target roles/skills. Score threshold is hardcoded at 3 in the Code node.
6. Activate.

Deliberately no LinkedIn/Indeed scraping (ToS) and no invented RSS feed URLs — add n8n's built-in RSS Feed Read node yourself later if you find a real Dutch job-board feed.
