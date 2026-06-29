# Data Sharing Setup

**Status:** Established 2026-06-29

This document describes the data sharing architecture for the WarSignalsThesis project: how code, data, and compute are organized across multiple machines and Google Colab.

---

## Architecture Overview

```
┌─────────────────────────────────┐
│ GitHub: katerynavalenia/        │
│         WarSignalsThesis        │
│  (code, configs, docs,         │
│   small files only)             │
└─────────────────────────────────┘
              ↑↓ git
              │ (5 KB)
┌─────────────────────────────────┐
│ Google Drive:                   │
│  WarSignalsThesis_Data/         │
│  (large data files, 5+ GB)     │
└─────────────────────────────────┘
              ↑↓
        ┌─────┴─────┬─────────┐
        │           │         │
   [Local PC]  [Colab]   [Other PCs]
   (30 GB RAM) (13 GB)   (varies)
```

**Key principle:** GitHub holds **code** (small, version-controlled). Google Drive holds **data** (large, shared, no version control needed).

---

## What's Where

### GitHub Repository (`katerynavalenia/WarSignalsThesis`)
- `src/` — Python modules
- `scripts/` — Standalone processing scripts
- `notebooks/` — Jupyter notebooks (local + Colab)
- `config/` — YAML configs (`source_groups.yaml`, `country_groups.yaml`, etc.)
- `docs/` — Documentation (this file, phase audits, data dictionary)
- `tests/` — Unit tests
- `requirements.txt` — Python dependencies
- `.gitignore` — Excludes secrets, large data, build artifacts

**Maximum file size in GitHub:** 100 MB per file. We never commit data files.

### Google Drive (`WarSignalsThesis_Data/`, folder ID: `1i1kkelDYszQ5Bi5Hv94NGT6wjCHkbIWU`)
- `data/raw_enriched/` — 5.1 GB, 184 parquet files (GDELT GKG with TONE, COUNTRIES, PERSONS, ORGS, THEMES)
- `data/processed/news/` — Pipeline outputs (deduped, classified, daily aggregates)
- `data/interim/` — Working files (chunked classifications during pipeline runs)
- `models/` — Trained ML models (future)
- `outputs/` — Figures, tables, reports (future)

**Size limit:** 15 GB free (Google account). If we exceed, upgrade to 100 GB (~$2/month) or 2 TB (~$10/month).

---

## Setup Instructions (Per Machine)

### Prerequisites
- Linux/macOS/WSL
- Python 3.11+ in a virtual environment
- Git
- rclone (`sudo apt install rclone` or `brew install rclone`)

### Step 1: Clone the Repository
```bash
git clone https://github.com/katerynavalenia/WarSignalsThesis
cd WarSignalsThesis
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Step 2: Configure rclone for Google Drive

#### One-time setup (per machine):
```bash
mkdir -p ~/.config/rclone

cat > ~/.config/rclone/rclone.conf << 'EOF'
[gdrive]
type = drive
client_id = YOUR_CLIENT_ID.apps.googleusercontent.com
client_secret = YOUR_CLIENT_SECRET
scope = drive
token = 
root_folder_id = 
tps_limit = 10
EOF
```

To get `client_id` and `client_secret`:
1. Go to [console.cloud.google.com](https://console.cloud.google.com/) → your project (e.g. `warsignals-thesis`)
2. APIs & Services → Credentials → Create Credentials → OAuth 2.0 Client ID (Desktop app)
3. Copy the Client ID and Client Secret into the config above

Then authorize (one-time browser flow):
```bash
rclone authorize drive
```

This opens a browser, you log in to Google, grant Drive access, and rclone saves the refresh token to `~/.config/rclone/rclone.conf`.

**Note:** The `client_id` and `client_secret` above are from the OAuth Desktop client created in the `warsignals-thesis` Google Cloud project. If you need to regenerate them, go to [console.cloud.google.com](https://console.cloud.google.com/) → APIs & Services → Credentials.

#### Verify connection:
```bash
rclone lsf gdrive:WarSignalsThesis_Data
# Should show: data/  models/  outputs/
```

### Step 3: Download Data from Drive (Optional)

If you want a local copy of the 5.1 GB raw data:
```bash
rclone copy gdrive:WarSignalsThesis_Data/data/raw_enriched \
  data/news_colab_sim/war_signals_phase3/raw_enriched \
  --transfers 4 --tpslimit 10 --progress
```

**Skip this step if you plan to use Colab** — Colab can read directly from Drive.

### Step 4: Run the Pipeline

The pipeline reads from `data/news_colab_sim/war_signals_phase3/raw_enriched/` and writes to `data/processed/news/`. Both can be local or on Drive.

**Local execution (if you downloaded data):**
```bash
python scripts/phase3_post_process_enriched.py
```

**Colab execution** — see `notebooks/colab_03b_phase3_pipeline.ipynb` (mount Drive, run pipeline, save to Drive).

---

## Google Colab Workflow

### One-time setup per Colab session:

1. **Open the notebook:**
   - Go to [colab.research.google.com](https://colab.research.google.com/)
   - `File → Open notebook → GitHub` tab
   - Search: `katerynavalenia/WarSignalsThesis`
   - Open: `notebooks/colab_03b_phase3_pipeline.ipynb`

2. **Run the setup cells** (the notebook will):
   - Mount your Google Drive
   - Clone the repository
   - Symlink `data/` to Drive
   - Install dependencies

3. **Run the pipeline cells** to process the data.

4. **Outputs are saved back to Drive** at `WarSignalsThesis_Data/data/processed/news/`.

### Why Colab?
- 12.7 GB RAM (free) or 35 GB (Pro+) — more than local 30 GB if other apps are running
- No local disk space used
- GPU available for future ML training
- Free with your subscription

---

## Security Notes

### What's safe to commit to GitHub:
- ✅ All code (`src/`, `scripts/`, `notebooks/`)
- ✅ All configs (`config/*.yaml`)
- ✅ All docs (`docs/*.md`)
- ✅ All tests (`tests/`)
- ✅ `requirements.txt`

### What MUST NOT be committed:
- ❌ Google OAuth credentials (`client_secret_*.json`)
- ❌ Any API keys, tokens, passwords
- ❌ Large data files (parquet, csv, etc.)
- ❌ Trained models (until we set up proper version control for them)
- ❌ Personal notes or temporary files

All of these are in `.gitignore`. Verify before committing:
```bash
git status
# Should only show .py, .yaml, .md, .ipynb files
```

### OAuth Client Security
The `client_id` and `client_secret` in `rclone.conf` are **public-safe** (they're embedded in the OAuth Desktop app). However:
- The **refresh token** (auto-saved by `rclone authorize`) is sensitive — it grants Drive access to whoever has it
- Keep `~/.config/rclone/rclone.conf` readable only by you: `chmod 600 ~/.config/rclone/rclone.conf`
- Never commit `rclone.conf` to git

---

## Maintenance

### Uploading new data
```bash
# Upload a single file
rclone copy /local/path/file.parquet gdrive:WarSignalsThesis_Data/data/processed/news/

# Upload a directory
rclone copy /local/dir/ gdrive:WarSignalsThesis_Data/data/processed/news/ --progress

# Sync (mirror — deletes files in destination not in source!)
rclone sync /local/dir/ gdrive:WarSignalsThesis_Data/data/processed/news/
```

### Downloading from Drive
```bash
# Download to local
rclone copy gdrive:WarSignalsThesis_Data/data/processed/news/ ./data/processed/news/ --progress

# List files
rclone lsf gdrive:WarSignalsThesis_Data/data/processed/news/

# Check size
rclone size gdrive:WarSignalsThesis_Data/
```

### Monitoring Drive usage
```bash
rclone about gdrive:
# Shows total/used/free space
```

---

## Troubleshooting

### "directory not found" errors
The folder structure in Drive must exist before uploading. If you deleted it accidentally:
```bash
rclone mkdir gdrive:WarSignalsThesis_Data/data/raw_enriched
rclone mkdir gdrive:WarSignalsThesis_Data/data/processed/news
# etc.
```

### 429 rate limit errors
rclone automatically retries with exponential backoff. If persistent:
```bash
# Reduce speed
rclone copy ... --tpslimit 5 --transfers 2
```

### OAuth token expired
```bash
rclone config reconnect gdrive:
# Or re-authorize
rclone authorize drive
```

### "Failed to create file" or "quota exceeded"
Check Drive storage:
```bash
rclone about gdrive:
```
If full, either:
- Delete old files from Drive
- Upgrade Google One plan
- Move old data to a different storage backend

---

## Drive Folder IDs (for reference)

| Folder | ID | Purpose |
|---|---|---|
| `WarSignalsThesis_Data/` | `1i1kkelDYszQ5Bi5Hv94NGT6wjCHkbIWU` | Project root |
| `data/raw_enriched/` | `16fj3xVLMzKGsrf0kvU5mY91JV_e5Czz8` | 5.1 GB GDELT data |
| `data/processed/news/` | (get via `rclone lsjson`) | Pipeline outputs |
| `models/` | `1jILX3t4EUOQ1j7D9o9x4BwcI6X6UrrRD` | Trained models (future) |
| `outputs/` | `1wl6-gwfvdgS85Og2y3YAFLZSrocimAbQ` | Figures/tables (future) |

---

## Team Onboarding

For new team members:

1. **Get Drive access:** Ask the project owner to share the `WarSignalsThesis_Data` folder with your Google account (read+write).
2. **Install rclone** and follow Steps 1-2 above.
3. **Authorize rclone** with your own Google account.
4. **Verify access:**
   ```bash
   rclone lsf gdrive:WarSignalsThesis_Data/data/raw_enriched | head -5
   # Should show some parquet files
   ```
5. **Clone the repo** and start working.

That's it. No manual file sharing, no zip files, no email attachments.

---

## Cost Analysis

| Component | Cost | Notes |
|---|---|---|
| GitHub repo | Free | Public or private, both work |
| Google Drive (15 GB) | Free | Enough for current data |
| Google Drive (100 GB) | $1.99/month | If we exceed 15 GB |
| Google Drive (2 TB) | $9.99/month | If we have ML models, lots of outputs |
| Google Colab Free | $0 | 12.7 GB RAM, may disconnect |
| Google Colab Pro | $9.99/month | 35 GB RAM, longer runtimes, priority GPU |
| rclone | Free | Open source |

**Current monthly cost:** $0 (all within free tiers)
**Projected cost if we upgrade:** $10-20/month for 2 TB Drive + Colab Pro

---

## Future Considerations

### If we need more storage:
- Move old/intermediate data to a cheaper tier (e.g., AWS S3 Glacier: $0.004/GB/month)
- Or use Hugging Face Hub for ML datasets (free, designed for this)

### If we need version control for data:
- Add **DVC** (Data Version Control) on top of Drive
- Data versions tracked in git, stored in Drive
- See: https://dvc.org/doc/use-cases/data-registers

### If we need more compute:
- Upgrade Colab to Pro+ ($49.99/month for A100 GPU)
- Or use cloud VMs (Lambda Labs, Vast.ai for cheap GPUs)
- Or institutional HPC (if available)

---

## References

- rclone documentation: https://rclone.org/drive/
- Google Drive API quotas: https://developers.google.com/drive/api/guides/limits
- GDELT project: https://www.gdeltproject.org/
- Our GKG extraction: `docs/phase3_gdelt_audit.md`
