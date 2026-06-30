---
name: rclone-drive-sync
description: 'Sync the thesis data between local /home/mykyta/Desktop/katya/WarSignalsThesis and Google Drive folder WarSignalsThesis_Data. Use when the user says "sync to drive", "upload to drive", "download from drive", "pull results", "push data", "rclone", or after any Colab pipeline run completes. Handles OAuth re-auth automatically when the token expires (every ~1 hour).'
---

# Drive Sync via rclone

## When to Use

Invoke this skill when the user wants to:
- Download processed data from Google Drive back to local (after Colab run)
- Upload newly generated outputs to Drive (after local pipeline run)
- Verify what's on Drive vs local
- Refresh the rclone OAuth token

**Triggers:** "sync to drive", "upload", "download", "pull from drive", "push to drive", "rclone", "sync data", "get latest results".

## Setup (assumed already configured)

- rclone v1.60+ installed via `apt`
- OAuth client in `~/.config/rclone/rclone.conf` under `[gdrive]`:
  - `client_id = 404655292731-q3r3d05o0d9470q79v7739m27vgcma7b.apps.googleusercontent.com`
  - `client_secret` is present (do not expose in chat)
  - `scope = drive`
- Google Drive folder `WarSignalsThesis_Data/` (root folder ID: `1i1kkelDYszQ5Bi5Hv94NGT6wjCHkbIWU`)
- Subfolder structure:
  - `data/raw_enriched/` — 184 raw GKG parquets (5.1 GB)
  - `data/processed/news/` — pipeline output (9.4 GB, includes 4.7 GB classified parquet)
  - `data/interim/`, `models/`, `outputs/` — other artifacts

## Procedure

### Step 1: Test current auth

```bash
cd ~/Desktop/katya/WarSignalsThesis && source .venv/bin/activate
rclone lsf gdrive:WarSignalsThesis_Data/ 2>&1 | head -5
```

- **If it works** → skip to Step 3.
- **If it fails with `unauthorized_client`** or `couldn't fetch token` → go to Step 2.

### Step 2: Re-authenticate (token expired)

The OAuth access token expires after ~1 hour. The refresh token also eventually gets rejected by Google ("unauthorized_client" means the entire OAuth client is dead and needs full re-auth). Re-auth takes ~10 seconds of user action.

Run the helper script:

```bash
bash .github/skills/rclone-drive-sync/scripts/reauth.sh
```

The script will:
1. Back up current `~/.config/rclone/rclone.conf` to `rclone.conf.bak`
2. Strip the bad token from the config
3. Start `rclone authorize drive` in the background
4. Print the OAuth URL: open it in the user's browser
5. Wait up to 120 seconds for the user to complete the flow
6. Parse the new token from the log
7. Save it back to the rclone config
8. Verify auth works

If the script fails, the user can complete the flow manually:

```bash
# Start the auth
unset BROWSER
nohup rclone authorize drive > /tmp/rclone_auth.log 2>&1 &
sleep 5
cat /tmp/rclone_auth.log  # shows the URL

# After user completes the browser flow, parse the token
python -c "
import re, json, configparser
log = open('/tmp/rclone_auth.log').read()
match = re.search(r'--->\s*(\{.*?\})\s*<---', log, re.DOTALL)
if match:
    token_data = json.loads(match.group(1).strip())
    config = configparser.ConfigParser()
    config.read('/home/mykyta/.config/rclone/rclone.conf')
    config['gdrive']['token'] = json.dumps(token_data)
    with open('/home/mykyta/.config/rclone/rclone.conf', 'w') as f:
        config.write(f)
    print('✓ Token saved, expires:', token_data['expiry'])
"
```

### Step 3: Run the sync

**Upload (local → Drive)** — use when local has newer files:

```bash
rclone copy --update --progress \
  data/processed/news/ \
  gdrive:WarSignalsThesis_Data/data/processed/news/
```

**Download (Drive → local)** — use when Drive has newer files (e.g., after Colab run):

```bash
rclone copy --update --progress \
  gdrive:WarSignalsThesis_Data/data/processed/news/ \
  data/processed/news/
```

**Always include `--update`** — this skips files that are newer on the destination, preventing accidental overwrites.

### Step 4: Verify the sync

```bash
echo "=== DRIVE ==="
rclone lsf --format "ts" gdrive:WarSignalsThesis_Data/data/processed/news/
echo "=== LOCAL ==="
ls -lh data/processed/news/
```

Compare timestamps and sizes — they should match (or local should be newer if you just uploaded).

For raw data (5.1 GB), the first download takes ~30 min. Subsequent `--update` runs are fast (only check sizes/hashes).

## Common path mappings

| Purpose | Local | Drive |
|---------|-------|-------|
| Raw enriched GKG (5.1 GB, 184 files) | `data/news_colab_sim/war_signals_phase3/raw_enriched/` | `gdrive:WarSignalsThesis_Data/data/raw_enriched/` |
| Processed news (9.4 GB) | `data/processed/news/` | `gdrive:WarSignalsThesis_Data/data/processed/news/` |
| Interim data | `data/interim/` | `gdrive:WarSignalsThesis_Data/data/interim/` |
| Models | `models/` | `gdrive:WarSignalsThesis_Data/models/` |
| Figures / tables | `outputs/figures/`, `outputs/tables/` | `gdrive:WarSignalsThesis_Data/outputs/` |

## Troubleshooting

### "rclone: command not found" (on Colab)
This skill is for **local machine** use only. Colab has no rclone. Use `notebooks/colab_03b_phase3_pipeline.ipynb` Cell 7 instead.

### "Permission denied" during OAuth
The Google Sign-in page may show a warning screen ("Google hasn't verified this app"). Click "Advanced" → "Go to rclone (unsafe)". This is expected because rclone is a personal OAuth app, not a Google-verified product.

### "Failed to create file system" (unauthorized_client)
The refresh token is dead. Run Step 2 (re-auth) again.

### Sync stuck at 0% for a long time
The first transfer of a large file (4.7 GB) can take 15-30 min. Check progress:
```bash
tail -20 /tmp/rclone_download.log
```

## Important constraints

- **NEVER commit `~/.config/rclone/rclone.conf` to git** — it contains a working OAuth token. The token in the docs was redacted after a secret-scanning incident; the actual config is gitignored.
- **Token expires every ~1 hour** — re-auth is a normal part of the workflow, not an error.
- **Always use `--update`** — without it, rclone overwrites newer files with older ones (data loss).
- **5.1 GB raw data is not in git** — it's in Drive only. See `.gitignore` rule: `data/news_colab_sim/**/*.parquet`.

## Related files

- [docs/data_sharing.md](../../../docs/data_sharing.md) — full architecture explanation
- [notebooks/colab_03b_phase3_pipeline.ipynb](../../../notebooks/colab_03b_phase3_pipeline.ipynb) — Colab-side pipeline that writes to Drive
- [scripts/verify_setup.py](../../../scripts/verify_setup.py) — verifies rclone config and Drive access
