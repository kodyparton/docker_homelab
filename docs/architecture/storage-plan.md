# Storage Optimization & Migration Plan

Drafted 2026-08-26. **Phases 1 and 2 executed 2026-08-27 — see "Results" at the bottom.** Phase 3 deliberately not done. All figures measured from the live system.

## Current state

Boot volume: **228GB total, ~41GB free (80% used)** — and that's *after* reclaiming 34GB from Plex's thumbnail cache earlier today. Without that, adding Immich/Paperless/Vaultwarden wouldn't have fit at all. The trend is the problem, not today's number.

Where the space actually goes:

| Item | Size | Movable? |
|---|---|---|
| **OrbStack VM** (`~/Library/Group Containers/…orbstack/data`) | **28GB** | Yes, but with a serious caveat — see below |
| Plex Media Server data (metadata, plug-ins, bundles) | 12GB | **Yes, cleanly** — Plex supports relocation |
| Claude Desktop (`vm_bundles` 9GB) | 10GB | Not ours to touch |
| Repo bind-mount data (`~/Documents/docker/*/`) | ~9GB | Yes — `ollama/` alone is 4.6GB |
| /Applications | 5.8GB | No |
| macOS itself + system | ~80GB | No |

Docker images alone are **23GB across 31 images, 0 bytes reclaimable** — everything is actively used, so pruning won't help again. The stack simply grew.

## Three tiers, and what belongs on each

The important design point: **these three storage targets have very different reliability characteristics**, and that — not capacity — should decide what goes where.

| Tier | Capacity | Reliability | Right for |
|---|---|---|---|
| **Internal SSD** | 228GB (41GB free) | Highest — always attached | OS, live databases, anything whose corruption would be painful |
| **USB 4TB SSD** | 4TB | Good speed, **but detachable** | Bulk app data, regenerable caches, Docker images, cold data |
| **NAS (UniFi)** | 44TB (23TB free) | Huge, but **SMB passthrough is known-flaky** (workflow 09 exists specifically to restart containers when mounts drop) | Media files, backups, archives — **never live databases** |

**The NAS is explicitly wrong for databases.** SMB + a database that expects POSIX locking is a corruption risk, and this setup already has documented mount-drop incidents. Media and backups only.

## Hard constraints — read before buying into any of this

### 1. The USB SSD must be formatted **APFS**, not exFAT
This is a blocker, not a preference. exFAT and FAT32 have no concept of Unix ownership or permissions, which breaks:
- every `linuxserver.io` container (they rely on `PUID`/`PGID` 1000)
- `unpackerr`, which runs as an explicit `user: 1001:988`
- **Postgres, which refuses to start** if its data directory permissions are wrong (affects Immich and Infisical)

If the drive is currently exFAT (common for drives sold cross-platform), it needs reformatting — which erases it.

### 2. USB detachment is a real risk for an always-on server
If the drive disconnects or sleeps mid-write, anything with an open database on it can corrupt. Mitigations, in order of preference:
- Keep live databases on the **internal** SSD; put only bulk/regenerable data on USB
- Connect directly, not through a hub
- Disable disk sleep for external drives
- If a database *must* live there, make sure it's in the backup rotation first

### 3. Mount-point stability
macOS mounts external drives at `/Volumes/<name>`, and after an unclean unmount it can silently become `/Volumes/<name> 1`. Bind mounts pointing at the old path then resolve to an *empty directory* rather than failing loudly — containers start "fine" and see no data. Worth mounting by UUID via `/etc/fstab`, or at minimum adding a startup check that the expected path is non-empty before Docker starts.

### 4. Moving OrbStack's storage means starting from a blank slate
OrbStack lets you change its storage location (Settings → Storage), but **it does not migrate existing data** — you get an empty Docker install. There is no supported export/import.

**The good news, specific to this setup**: I checked, and this stack is unusually portable. Only **one** container keeps state inside the VM:

- `n8n_n8n_data` — **51MB**, holds workflows and credentials
- Everything else (all 34 other containers) bind-mounts to `~/Documents/docker/*/`, which lives on the host and is untouched by a VM rebuild

So a rebuild costs: re-pulling 23GB of images, and `docker compose up -d` in each service directory. All compose files are git-tracked. The 28 workflow JSONs are already backed up in git; n8n **credentials** would need re-entering, though most values now live in Infisical.

## Recommended plan, in priority order

### Phase 1 — Free space with zero migration risk (do first regardless)
No service moves; nothing can break.

1. **Redirect backups to the NAS.** `infisical/backups/` and `qdrant/snapshots/` currently write to the boot disk. Pointing them at the NAS frees space *and* closes the "backups sit on the same disk as the originals" gap flagged previously. Highest value-to-risk ratio on this list.
2. **Cap Docker log sizes.** Container JSON logs grow unbounded; one was already 16MB. A global `log-opts` limit prevents slow leakage.
3. **Set up an automated Plex cache trim.** The 34GB `PhotoTranscoder` reclaim was manual. It will grow back — this should be a scheduled job, not something rediscovered at 95% full.

Estimated recovery: **several GB immediately, plus stops the bleeding.**

### Phase 2 — Move bulk data to the USB SSD (low risk, good win)
Once the drive is APFS-formatted and stably mounted:

4. **Plex Media Server data (12GB)** → USB. Officially supported by Plex, metadata is regenerable, and it's the largest clean win. Plex must be stopped during the copy.
5. **Ollama models (4.6GB)** → USB. Re-downloadable if lost, so low stakes. They're read during inference, but a fast SSD is fine for this. Note: bigger benefit than it looks, since model files are the single largest bind-mount.
6. **Immich thumbnail/encoded-video cache** → USB, keeping its Postgres on internal. Immich generates a lot of derived files; those are regenerable, its database is not.

Estimated recovery: **~17GB off the boot disk.**

### Phase 3 — Move the OrbStack VM (biggest win, highest effort)
Only if Phases 1–2 don't buy enough runway.

7. Back up `n8n_n8n_data` (51MB) and export n8n credentials.
8. Change OrbStack storage location to the USB SSD.
9. `docker compose up -d` across all service directories; restore the n8n volume.
10. Verify every service, especially the ones with databases.

Estimated recovery: **~28GB.** Cost: a rebuild, and the stack runs from USB — meaning a disconnect takes everything down. **My recommendation: treat this as a last resort**, or reconsider whether the Mac Mini's internal drive should simply be the thing that gets upgraded.

## What I'd actually suggest

Do **Phase 1 now** — it's pure upside, no migration, and fixes the backup-location problem at the same time. Then **Phase 2** when the drive is ready and confirmed APFS.

Hold off on Phase 3. Moving the entire Docker VM onto a detachable drive, on a machine that runs 35 containers including four databases, trades a disk-space problem for an availability problem. Phases 1 and 2 should recover ~20GB+, which on current growth is a lot of runway.

## What I need from you before implementing

1. **Connect the SSD** and tell me — I'll check its filesystem. It wasn't attached when this was drafted.
2. **Confirm it can be erased** if it turns out to be exFAT (reformatting to APFS destroys its contents).
3. **Which phase(s) to proceed with.**
4. Worth considering separately: is upgrading the Mac Mini's internal storage (or moving to a machine with more) the better long-term answer than layering external drives onto an always-on server?


---

# Results — Phases 1 & 2 executed 2026-08-27

## The drive

WD_BLACK 4TB (`/dev/disk4`), was exFAT holding 1.2TB of media. **Before erasing, every one of its 49 items was verified to also exist on the NAS** — nothing unique was lost. Reformatted APFS as `FastSSD` (3.6TB usable).

**Caveat found and worth remembering: the volume has `Owners: Disabled`.** `chown` inside a container *reports success but does not stick* — files stay root-owned. This did not affect what was migrated (Plex is a native macOS app; Ollama's container runs as root), but it **does block** moving anything uid-sensitive there — Postgres and every `linuxserver.io` PUID/PGID container included. Enabling it needs an interactive sudo:

```
sudo diskutil enableOwnership /Volumes/FastSSD
```

Run that before considering any database or *arr service for this drive.

## Phase 1 — done

- **Backups now write to the NAS** (`/Volumes/media/backups/`), not the boot disk. Workflow 03 updated and both commands executed live to prove they work: the Infisical dump on the NAS was decompressed and verified to contain 189 `CREATE TABLE` statements, not just "a file exists". Qdrant snapshots sync to the NAS keeping 14 there and only the newest locally. This also closes the "backups sit on the same disk as the originals" gap.
- **Docker log rotation** set to 10MB×3 in `~/.orbstack/config/docker.json`. **Honest correction: this turned out to be a non-issue.** OrbStack already defaults to 20MB×5 per container, and total logs across all 35 containers were only 41MB. The tighter setting applies to newly-created containers; not worth restarting the whole stack to backfill.
- **`scripts/disk_maintenance.sh`** added — report-only by default, `--apply` to act. Trims Plex's PhotoTranscoder cache only once it exceeds 10GB, prunes dangling Docker images, and *reports* other large caches without touching them. This exists because the 34GB PhotoTranscoder reclaim on 2026-08-26 was manual and it grows back.

## Phase 2 — done

| Moved | Size | Verification |
|---|---|---|
| Plex Media Server data → `/Volumes/FastSSD/PlexData` (symlinked) | 12GB | DB byte-identical (144,438,272 bytes) and 13,584 metadata items readable in the copy *before* the original was removed. After restart: same `machineIdentifier`, all 4 libraries, item counts 218/493/81/13 matching pre-move. |
| Ollama models → `/Volumes/FastSSD/ollama/config` | 4.6GB | Both models load from SSD; a real inference call returned correctly; then a full second-brain round trip through Discord's webhook succeeded. |

**Boot volume: 24GB → 42GB free.**

## Unexplained growth — open item

Free space measured **41GB at the start of the session, 24GB partway through**, before any migration ran — roughly 17GB consumed by something other than this work. Accounted for: ~4GB of Plex rebuilding caches after the 2026-08-26 clear. The remaining ~13GB is **not explained**. Ruled out: Time Machine local snapshots (deleted one, no change), Docker (unchanged at 28GB), the repo (unchanged), and Spotlight indexing the new SSD (that index lives on the SSD).

Phase 2's 18GB recovery roughly cancelled it out, which means **the underlying consumer may still be active**. Worth watching `df -h /System/Volumes/Data` over a few days. A candidate not yet ruled out is the Photos library / iCloud downloading originals — `du` on it timed out rather than returning a figure.

## Phase 3 — still not recommended

Moving the OrbStack VM (28GB) would put 35 containers and four databases on a detachable drive. The `Owners: Disabled` finding above makes it worse: Postgres would need volume ownership enabled first. Given Phases 1-2 recovered enough headroom, the better long-term answer remains upgrading the Mini's internal storage rather than layering external drives onto an always-on server.
