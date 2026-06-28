# Phase 3 — GDELT Extraction and Source Classification

**Date:** TBD (filled after extraction completes)
**Scope:** GDELT DOC 2.0 multilingual article extraction, 2022-09-29 → 2026-06-21
**Status:** ⏳ Pending (template — to be completed after Colab run)

---

## 1. Executive Summary

_This audit will be populated after the Colab extraction completes. Placeholder sections follow._

The pipeline:

1. **Extraction** — 4 multilingual queries × 46 monthly windows = ~180 API calls to GDELT DOC 2.0
2. **Deduplication** — MinHash + LSH on article titles (5-gram shingles, Jaccard ≥ 0.7)
3. **Source classification** — Domain → group lookup (Ukrainian / Russian / Western / Other)
4. **Language detection** — `langdetect` on titles
5. **Daily aggregation** — Article counts by date and source group
6. **Manual precision audit** — 100 articles sampled (25 per group) for hand-labeling

---

## 2. Pipeline Architecture

### 2.1 Source files

- `src/data/gdelt.py` — importable module
- `config/gdelt_queries.yaml` — multilingual keyword dictionary
- `config/source_groups.yaml` — domain → group mapping
- `notebooks/colab_03_gdelt_extraction.ipynb` — Colab pipeline
- `tests/test_gdelt.py` — 21 unit tests (all passing)

### 2.2 Configuration summary

- **Queries:** 4 (russian_attack_direct, ukraine_defense_energy, defense_industry_western, energy_war)
- **Languages:** English, Russian, Ukrainian, German, French, Polish
- **Source groups:** Ukrainian (29 domains), Russian (47), Western (180+), Other (catch-all)
- **Dedup:** 5-gram shingles, 128 permutations, 0.7 Jaccard threshold

---

## 3. Execution Summary (to be filled after Colab run)

### 3.1 Wall time

| Cell | Wall time | Status |
|---|---|---|
| Cell 1: Setup | _min_ | ⏳ |
| Cell 2: Load config | _sec_ | ⏳ |
| Cell 3: Smoke test | _sec_ | ⏳ |
| Cell 4: Full extraction | _min_ | ⏳ |
| Cell 5: Deduplication | _min_ | ⏳ |
| Cell 6: Classification | _min_ | ⏳ |
| Cell 7: Daily aggregation | _sec_ | ⏳ |
| Cell 8: Summary | _sec_ | ⏳ |

### 3.2 Output files

| File | Size | Status |
|---|---|---|
| `data/interim/news/gdelt_articles_raw.parquet` | _MB_ | ⏳ |
| `data/interim/news/gdelt_articles_dedup.parquet` | _MB_ | ⏳ |
| `data/interim/news/gdelt_articles_classified.parquet` | _MB_ | ⏳ |
| `data/processed/news/news_daily.parquet` | _MB_ | ⏳ |
| `data/processed/news/source_classification_table.csv` | _KB_ | ⏳ |
| `data/processed/news/manual_precision_audit.csv` | _KB_ | ⏳ |

---

## 4. Data Quality (to be filled)

### 4.1 Source distribution

| Source group | Articles | % | Top 3 domains |
|---|---|---|---|
| Ukrainian | _%_ | _domains_ |
| Russian | _%_ | _domains_ |
| Western | _%_ | _domains_ |
| Other | _%_ | _domains_ |

### 4.2 Language distribution

| Language | Articles | % |
|---|---|---|
| English | _%_ | |
| Russian | _%_ | |
| Ukrainian | _%_ | |
| German | _%_ | |
| French | _%_ | |
| Polish | _%_ | |
| Other/Unknown | _%_ | |

### 4.3 Dedup ratio

| Step | Articles | Reduction |
|---|---|---|
| Raw | _%_ | 0% |
| After MinHash/LSH | _%_ | _%_ |

### 4.4 Precision audit results

(To be filled after manual labeling)

| Source group | Sampled | Relevant | Precision |
|---|---|---|---|
| Ukrainian | 25 | _%_ | _%_ |
| Russian | 25 | _%_ | _%_ |
| Western | 25 | _%_ | _%_ |
| Other | 25 | _%_ | _%_ |
| **Total** | **100** | _%_ | _%_ |

---

## 5. Critical Issues for Resolution

_To be filled after extraction completes._

---

## 6. Deliverables (Phase 3 completion)

- [x] **Multilingual query dictionary** — `config/gdelt_queries.yaml`
- [x] **Source group classification** — `config/source_groups.yaml`
- [x] **Reproducible extraction pipeline** — `src/data/gdelt.py`
- [x] **Colab notebook** — `notebooks/colab_03_gdelt_extraction.ipynb`
- [x] **Colab setup instructions** — `docs/colab_03_setup.md`
- [ ] **Raw articles** — `data/interim/news/gdelt_articles_raw.parquet` (after Colab run)
- [ ] **Deduped articles** — `data/interim/news/gdelt_articles_dedup.parquet` (after Colab run)
- [ ] **Classified articles** — `data/interim/news/gdelt_articles_classified.parquet` (after Colab run)
- [ ] **Daily aggregates** — `data/processed/news/news_daily.parquet` (after Colab run)
- [ ] **Manual precision audit** — `data/processed/news/manual_precision_audit.csv` (after manual labeling)
- [ ] **Field dictionary updates** — `docs/data_dictionary.md`
- [ ] **Project status updates** — `docs/project_status.md`

### Completion criterion (master plan §6.3)

> "A manually reviewed sample shows that most retained articles concern Russian aerial attacks on Ukraine rather than unrelated war coverage."

_Result: To be filled after manual audit._

---

## 7. Next Steps (after audit)

- **Phase 4 (NLP features):** Multilingual transformer for sentiment, threat, escalation
- **Phase 5 (Merge + features):** Combine `news_daily.parquet` with `attack_daily.parquet` and `financial_daily.parquet` to produce `model_matrix.parquet`
- **Phase 6-7 (Models):** Run econometric and ML baselines with the new feature set
