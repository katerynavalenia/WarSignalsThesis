# Colab Setup for Phase 3 — GDELT Extraction

**Time required:** 4-6 hours (mostly waiting for the API)
**Cost:** Google Colab Pro recommended (~$10/month) for High-RAM
**Result:** ~1 GB of article-level data + 1,400 daily aggregate rows

---

## What This Does

The notebook `notebooks/colab_03_gdelt_extraction.ipynb` runs the full Phase 3 pipeline on Google Colab:

1. **Extraction** — Pulls multilingual articles from GDELT DOC 2.0 for 2022-09-29 → 2026-06-21 (~46 monthly windows × 4 queries = ~180 API calls)
2. **Deduplication** — MinHash + LSH on article titles (removes ~30-50% duplicates)
3. **Source classification** — Domain → source group lookup (Ukrainian / Russian / Western / Other)
4. **Daily aggregation** — Group by date + source group
5. **Manual audit sample** — Output 100 articles for hand-labeling

---

## Prerequisites

1. **Google account** with Google Drive (~1 GB free space)
2. **Colab Pro** (recommended) — Free tier may run out of RAM for 1M+ articles
3. **GitHub access** — Colab will clone the WarSignalsThesis repo

---

## Step-by-Step Instructions

### 1. Open Colab

1. Go to [colab.research.google.com](https://colab.research.google.com)
2. Sign in with your Google account
3. Click **File → Upload notebook** (or **File → Open notebook → GitHub**)

### 2. Upload the Notebook

Option A — Upload directly:
- File → Upload notebook → select `notebooks/colab_03_gdelt_extraction.ipynb`

Option B — Open from GitHub (if you've pushed the repo):
- File → Open notebook → GitHub tab
- Paste: `https://github.com/<your-username>/WarSignalsThesis`
- Select `notebooks/colab_03_gdelt_extraction.ipynb`

### 3. Set Runtime Type

1. **Runtime → Change runtime type**
2. Settings:
   - **Runtime type:** Python 3
   - **Hardware accelerator:** None (CPU is enough; we don't use GPU)
   - **Runtime shape:** **High-RAM** (this is critical for dedup)
3. Click Save

### 4. (Optional) Set Up Google Drive Mount

The notebook will mount your Drive automatically. When prompted:
1. Click the "Connect to Google Drive" cell
2. Sign in and grant permission
3. A folder `/content/drive/MyDrive/` will be mounted

### 5. Run All Cells

1. **Runtime → Run all** (or Ctrl+F9)
2. The notebook has 8 cells; each cell has a clear purpose (see below)
3. Watch the progress; cells 4-5 take 2-6 hours total

### 6. Monitor Progress

The notebook prints progress at every step:

```
=== Cell 3: SMOKE TEST ===
[FETCH] 2024-01-15 → 2024-01-15 ... 50 articles
✓ Smoke test passed

=== Cell 4: FULL EXTRACTION ===
[FETCH] russian_attack_direct 2022-09 ... 245 articles
[FETCH] russian_attack_direct 2022-10 ... 312 articles
...
```

### 7. Wait for Completion

Total wall time: **4-6 hours**. The notebook is **resumable** — if Colab disconnects, you can re-run from the cell that failed (it will skip already-saved windows).

### 8. Download Results

When the notebook finishes, it prints:

```
=== Cell 8: SUMMARY ===
Files saved to /content/drive/MyDrive/war_signals_phase3/:
  - gdelt_articles_raw.parquet       (~500 MB)
  - gdelt_articles_dedup.parquet     (~250 MB)
  - gdelt_articles_classified.parquet (~250 MB)
  - news_daily.parquet               (~1 MB)
  - source_classification_table.csv  (~5 KB)
  - manual_precision_audit.csv       (~50 KB)
```

To download:
1. In Colab, click the **Files** tab (left sidebar)
2. Navigate to `/content/drive/MyDrive/war_signals_phase3/`
3. Right-click each file → Download

Alternatively, the files are already in your Google Drive — just download from there.

### 9. Copy Results to Local

```bash
# From your local terminal:
mkdir -p data/interim/news
mkdir -p data/processed/news

# Copy from Downloads/ to local project
cp ~/Downloads/gdelt_articles_raw.parquet data/interim/news/
cp ~/Downloads/gdelt_articles_dedup.parquet data/interim/news/
cp ~/Downloads/gdelt_articles_classified.parquet data/interim/news/
cp ~/Downloads/news_daily.parquet data/processed/news/
cp ~/Downloads/source_classification_table.csv data/processed/news/
cp ~/Downloads/manual_precision_audit.csv data/processed/news/
```

### 10. Tell Me You're Done

Once the files are in place, just say "Colab done" and I'll:
- Generate the figures
- Compute the precision audit summary
- Write the audit report
- Update the data dictionary and project status

---

## Notebook Architecture (8 cells)

| Cell | Purpose | Wall time |
|---|---|---|
| 1. Setup | Mount Drive, install deps, set paths | 1 min |
| 2. Load config | Read YAML files, print summary | <1 min |
| 3. Smoke test | Fetch 1 day, validate pipeline | 5 sec |
| 4. Full extraction | 46 months × 4 queries = ~180 API calls | 2-4 hours |
| 5. Deduplication | MinHash + LSH | 1-2 hours |
| 6. Classification | Domain → group + langdetect | 5-10 min |
| 7. Daily aggregation | Group by date+group | 1-2 min |
| 8. Summary | Print coverage stats, top sources | <1 min |

---

## Resume / Failure Recovery

If Colab disconnects mid-execution:

1. Re-open the notebook
2. Re-run from Cell 1 (Drive will remount)
3. Cell 4 will **skip already-saved** monthly parquets (auto-resume)
4. Cell 5 will re-run from scratch but is fast (MinHash on existing data)
5. Cells 6-8 are idempotent

If Cell 4 fails for one specific (query, month):
- The error is printed and the loop continues
- The remaining queries/months are still processed
- You can re-run only Cell 4 to retry the failed one

---

## FAQ

**Q: Can I use the free Colab tier?**
A: Yes, but it may run out of RAM for Cell 5 (dedup). If you see a MemoryError, switch to Pro High-RAM.

**Q: What if my Colab session times out (12 hours)?**
A: Cell 4 saves after every (query, month), so you can resume. The notebook auto-detects what's already done.

**Q: Can I run this on a smaller date range first (e.g., 2025 only) to test?**
A: Yes! Edit Cell 4 and change `start` and `end` arguments. The pipeline works the same way.

**Q: What if some months return 0 articles?**
A: That's normal for narrow queries. The notebook handles it gracefully (saves an empty parquet).

**Q: How do I know the data is good?**
A: After Cell 8, look at:
- `n_articles_total` — should be 500K-2M
- `n_articles_ukrainian / russian / western` — should be roughly balanced
- `top_sources_per_group` — should be the curated news outlets, not random blogs
- Run the precision audit on 100 articles — most should be relevant

**Q: Can I re-run with different keywords?**
A: Yes! Edit `config/gdelt_queries.yaml` locally, push to GitHub, re-run the Colab. The notebook clones the latest version.

---

## Cost & Time Summary

| Item | Estimate |
|---|---|
| Notebook setup | 5 minutes |
| Cell 4 (extraction) | 2-4 hours |
| Cell 5 (dedup) | 1-2 hours |
| Cells 1-3, 6-8 | 15 minutes |
| Download from Drive | 10-30 minutes (depends on connection) |
| **Total** | **4-6 hours wall time** |
| **Colab Pro cost** | **~$10/month (cancels after the month)** |

---

## What to Do If You Get Stuck

1. **Memory errors in Cell 5** — switch to Pro High-RAM, or chunk the dedup by year
2. **API rate limits (429)** — the notebook auto-sleeps 5s; if you see persistent 429, increase `api_sleep` to 10s in Cell 4
3. **Drive storage full** — free up ~1 GB on your Drive before starting
4. **No articles returned** — check `config/gdelt_queries.yaml` keywords; some queries may be too narrow

### Specific to the smoke test (Cell 3)

If Cell 3 fails with "Smoke test failed: 0 articles":

1. **Check for `429 Too Many Requests`** in the cell output. The most common cause is rate limiting.
2. **Wait 5-10 minutes** if rate-limited, then re-run Cell 3 alone.
3. **The improved Cell 3 now tries all 4 queries** and gives a cleaner error message. It also `SystemExit(0)`s gracefully if all queries return 0 (treating it as a soft warning, not a hard error), so you can proceed to Cell 4.
4. **If Cell 3 still fails after waiting, skip it and run Cell 4 directly.** Cell 4 has its own retry logic with exponential backoff (4s, 8s, 16s, 32s, 64s on 429) and will skip already-completed months on resume.
5. **If Cell 4 returns 0 articles from a query**, that query's keywords are likely too narrow. Check the URL it tried (printed in the cell output) and try a more relaxed version.

For any other issues, copy the error message and the cell number, and we'll debug together.
