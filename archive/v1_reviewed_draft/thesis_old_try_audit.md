# Thesis Old Try Audit & Salvage Assessment

**Date:** 28 June 2026  
**Auditor:** AI Agent  
**Scope:** `thesis_old_try/` — previous firm-level causal panel regression attempt  
**Source of truth:** `Master_Thesis_Research_Completion_Plan.md` (predictive forecasting, index-level, daily, out-of-sample)

---

## 1. Executive Summary

The `thesis_old_try/` folder contains a complete **firm-level causal panel regression** study (event studies, DiD, panel OLS) that answered a different research question using a different methodology than the current plan. Nevertheless, several raw data assets and code components are salvageable.

### What CAN be salvaged

| Category | Items | Value to new project |
|---|---|---|
| Raw financial data | Bloomberg constituent-level prices for WAERLST (128 firms) and BSHIELDT (36 firms) 2020-2026 | **HIGH** — constituent data can reconstruct index; metadata useful |
| Raw benchmark data | indexes.xlsx with SPX, SXXP, VIX, Brent, EURUSD, MSCI World 2020-2026 | **HIGH** — directly usable as financial controls |
| Raw attack data | `missile_attacks_daily.csv` — 3,800+ attack records with weapon models, launched/destroyed, timestamps, sources | **HIGH** — core physical attack dataset for new plan |
| Weapon classification | `missiles_and_uavs-selected-columns.csv` — 65-row weapon reference table | **HIGH** — category dictionary |
| Raw GPR data | Daily GPRD with ACT/THREAT components + monthly GPRC_UKR/GPRC_RUS | **MEDIUM** — GPR is a control variable in new plan |
| Raw SIPRI data | Top 100 arms companies 2002-2024 | **LOW** — only needed for optional firm-level extension |
| Raw ACLED data | Weekly Ukraine conflict data | **LOW** — ACLED is not in the new plan's core |
| Parsing logic | Script 01 Bloomberg parsing | **MEDIUM** — parsing pattern reusable for index-level extraction |
| Weapon classification | Script 03 classification dictionary | **HIGH** — comprehensive weapon-type mapping |
| GPR processing | Script 04 GPR loading/merging | **MEDIUM** — can be adapted for new pipeline |

### What CANNOT be salvaged

- **All processed data files** — they are firm-level, not index-level; many contain look-ahead bias risks
- **All output tables/figures** — answer different research questions
- **Scripts 02, 05, 06, 07, 09-15** — designed for firm-level panel regression methodology
- **Old PDF requirements document** — superseded by `Master_Thesis_Research_Completion_Plan.md`

### Critical gaps identified for the new research plan

1. **No WAERLST/BSHIELDT index-level price series** in raw data — only constituent-level prices exist
2. **No source-group separation** in GDELT data — only aggregate topic counts, not Ukrainian/Russian/Western
3. **No article-level GDELT data** — only daily counts per topic
4. **No multilingual narrative or sentiment measures**
5. **No attack-surprise features**
6. **No narrative-gap features**
7. **No European index selected** for robustness

---

## 2. Raw Data Audit

### 2.1 Bloomberg Financial Data

#### WAERLST as of Jun 04 2026.xlsx

| Property | Value |
|---|---|
| **Size** | 9.84 MB |
| **Sheets** | `Worksheet`, `with formulas`, `values only` |
| **Worksheet sheet** | Constituent snapshot: Ticker, Name, Weight, Shares, Price (129 rows) |
| **values only sheet rows** | 2,357 (10 metadata + 2,347 daily price rows) |
| **values only sheet cols** | 119 (date + 118 ticker columns) |
| **Date range** | 2020-01-01 to 2026-06-04 |
| **Data type** | **Constituent-level prices** (close prices per constituent), NOT index-level |
| **Unique tickers** | 118 constituents |
| **Metadata fields** | Ticker, Name (short + full), Weight, Shares, Price, Country, Currency, Market Cap, BICS Industry |
| **Total-return vs price** | Appears to be **price level**, not total-return (no dividend adjustment visible) |
| **OHLC available** | **No** — only single price column per ticker |
| **Weekend/holiday** | Missing dates have NaN values |
| **WAERLST index-level** | **NOT PRESENT** — no column contains the WAERLST index time series itself |
| **Quality** | Clean, well-structured; some tickers have stale data at beginning/end |

#### BSHIELDT as of Jun 05 2026.xlsx

| Property | Value |
|---|---|
| **Size** | 6.31 MB |
| **Sheets** | `Worksheet`, `with formulas`, `values only` |
| **Worksheet sheet** | Constituent snapshot (36 European defense firms) |
| **values only sheet cols** | 36 ticker columns |
| **Data type** | Constituent-level prices (same format as WAERLST) |
| **BSHIELDT index-level** | **NOT PRESENT** |
| **Note** | Shares and weights differ from WAERLST (index-specific) |

#### indexes.xlsx

| Property | Value |
|---|---|
| **Size** | 0.57 MB |
| **Sheets** | `Worksheet`, `with formulas`, `values only` |
| **values only sheet cols** | 6 benchmark tickers |
| **Benchmarks** | SPX Index, SXXP Index, VIX Index, CO1 Comdty (Brent), EURUSD Curncy, NDDUWI Index (MSCI World) |
| **Date range** | 2020-01-01 to 2026-06-04 |
| **Rows** | 2,347 daily observations |
| **Data type** | Index level / futures close / FX rate |
| **Quality** | Clean; weekend dates present with NaN values |
| **Usability** | **DIRECTLY USABLE** for new plan's financial controls |

### 2.2 UAF Attack Data

#### missile_attacks_daily.csv

| Property | Value |
|---|---|
| **Rows** | 3,813 |
| **Date range** | 2022-09-29 to 2026-06-20 (earliest attack ~Sep 2022) |
| **Key columns** | `time_start`, `time_end`, `model`, `launch_place`, `target`, `launched`, `destroyed`, `not_reach_goal`, `affected region`, `source` |
| **Weapon models** | 60+ distinct models (Shahed, Kalibr, Iskander, Kinzhal, Zircon, X-101, etc.) |
| **Source links** | Facebook/social media posts from Ukrainian Air Force (`kpszsu`, `PvKPivden`) |
| **Attack types** | Nightly waves (18:00-09:00), daytime unknown UAVs, ballistic missiles |
| **Quality** | High — official Ukrainian military sources with direct links |
| **Date assignment** | `time_start` used as attack date; overnight attacks span two calendar days |
| **Revision risk** | Numbers may be revised; raw file appears to be a cumulative dataset |

#### missiles_and_uavs-selected-columns.csv

| Property | Value |
|---|---|
| **Rows** | 65 |
| **Content** | Weapon classification reference table: model, category, national_origin, type, launch_platform, name, name_NATO, in_service, designer, manufacturer |
| **Categories** | UAV, ballistic missile, cruise missile, loitering munition, surface-to-air missile, guided bomb |
| **Usability** | **HIGH** — comprehensive classification dictionary for weapon categorization |

### 2.3 GPR Data

#### data_gpr_daily_recent.xls

| Property | Value |
|---|---|
| **Rows** | ~2,400 |
| **Date range** | 2019-2026 |
| **Key columns** | GPRD, GPRD_ACT, GPRD_THREAT, GPRD_MA7, GPRD_MA30 |
| **Frequency** | Daily |
| **Quality** | Standard GPR daily index from Matteo Iacoviello's database |
| **Usability** | **MEDIUM** — GPR is a control variable; daily frequency matches |

#### data_gpr_export.xls

| Property | Value |
|---|---|
| **Content** | Country-specific GPR monthly indices |
| **Key columns** | GPRC_UKR, GPRC_RUS (Ukraine and Russia specific) |
| **Frequency** | Monthly |
| **Usability** | **LOW** — monthly frequency may not add value over daily GPRD |

### 2.4 ACLED Data

| File | Content | Usability |
|---|---|---|
| `ACLED Data_2026-06-18.csv` | Individual conflict event records | **LOW** — not in new plan's core |
| `Europe-Central-Asia_aggregated_data_up_to_week_of-2026-06-06.xlsx` | Weekly aggregated Ukraine data | **LOW** — weekly frequency, ACLED not in core |

### 2.5 SIPRI Data

| Property | Value |
|---|---|
| **File** | `SIPRI-Top-100-2002-2024 (2).xlsx` |
| **Content** | Top 100 arms companies 2002-2024 with arms revenue, total revenue, arms share |
| **Sheets** | One per year (2002-2024) |
| **Rows** | 100 per year |
| **Fields** | Rank, Company, Country, Arms revenues, Total revenues, Arms share % |
| **Usability** | **LOW** — only needed for optional firm-level extension |

---

## 3. Processed Data Audit

| File | Rows | Key Content | Reusable? | Notes |
|---|---|---|---|---|
| `prices_daily.csv` | 174,223 | Firm-level daily prices (128 tickers, 2020-2026) | **NO** | Firm-level, not index-level; would need full reprocessing |
| `returns_daily.csv` | 157,440 | Firm-level log returns with benchmark comparisons | **NO** | Firm-level; new plan needs index-level |
| `benchmarks_daily.csv` | 2,348 | SPX, SXXP, VIX, Brent, EURUSD, MSCI_World | **YES (raw data)** | Same as indexes.xlsx; raw file is the true source |
| `uaf_daily.csv` | 801 | Daily attack aggregation with WI and IR variables | **ADAPT** | Logic is reproducible; data needs re-audit for look-ahead bias |
| `gpr_daily.csv` | 2,374 | Daily GPR + monthly country GPR forward-filled | **ADAPT** | Reproducible from raw; GPR is a control in new plan |
| `gdelt_topics_daily.csv` | 2,364 | Daily article counts for 8 topics, log-transformed | **LOW** | No source-group separation; only aggregate English-language counts |
| `acled_daily.csv` | 2,374 | Weekly ACLED forward-filled to daily | **NO** | Not in new plan core |
| `firms_metadata.csv` | 128 | Firm metadata for WAERLST+BSHIELDT constituents | **REFERENCE** | Useful for understanding firm universe |
| `sipri_exposure.csv` | 128 | SIPRI defense exposure matched to firms | **REFERENCE** | Only for optional firm-level extension |
| `panel_main.csv` | 91,624 | Full firm-day panel with 96 columns | **NO** | Firm-level, old methodology; not reusable |
| `abnormal_returns.csv` | ~157K | CAPM abnormal returns | **NO** | Old methodology (event study) |
| `market_model_params.csv` | ~128 | CAPM alpha, beta per firm | **NO** | Old methodology |
| `size_daily.csv` | ~174K | Daily market cap | **NO** | Firm-level, not needed for index study |
| `car_panel.csv` | ~20K | Cumulative abnormal returns | **NO** | Old event study methodology |
| `regression_results.csv` | ~50 | Panel regression results | **NO** | Old results |
| `panel_event.csv` | ~40K | Event study panel | **NO** | Old methodology |
| `panel_useu.csv` | ~60K | US+Europe subsample panel | **NO** | Old methodology |
| `panel_full.csv` | ~200K | Full panel (all firms, all dates) | **NO** | Old methodology |

### Look-ahead bias assessment

The processed data files were generated by a single pipeline execution. The following risks are noted:

- **SIPRI matching** (Script 06): Uses 2020-2024 average arms share — if merged with daily returns in a predictive context, this uses full-sample information. **Potential look-ahead bias** for any predictive use.
- **GPR forward-fill** (Script 04): Forward-fills using the full calendar. This is appropriate for a historical dataset but would need recursive estimation for out-of-sample use.
- **GDELT topics** (Script 08): Downloaded retrospectively. The counts themselves are point-in-time retrievable, so no look-ahead bias if the raw API responses are preserved. However, the query terms could include future knowledge.
- **Price data**: Historical prices are backward-looking by nature; no look-ahead concern as long as returns are calculated using only past prices.

---

## 4. Script Audit

| Script | Purpose | Reuse Potential | Reusable Components | Adaptations Needed |
|---|---|---|---|---|
| **01** `bloomberg_parse.py` | Parse Bloomberg Excel files → prices + metadata | **MEDIUM** | Excel parsing pattern, metadata extraction logic, benchmark parsing | Must be adapted for index-level extraction; currently extracts constituent-level prices |
| **02** `market_model_ar.py` | CAPM market model → abnormal returns | **LOW** | Return calculation logic | New plan uses raw returns, not abnormal returns |
| **03** `uaf_variables.py` | Weapon classification + daily aggregation | **HIGH** | Weapon classification dictionary (`WEAPON_CLASS`), `classify_model()` function, aggregation logic | Must re-audit date assignment rules; add `market_information_date`; remove look-ahead in aggregation |
| **04** `gpr_variables.py` | GPR index processing | **MEDIUM** | GPR daily loading, column renaming, log-transform, forward-fill pattern | Must add recursive estimation for out-of-sample; GPR is a control variable |
| **05** `acled_variables.py` | ACLED conflict data processing | **LOW** | openpyxl workbook parsing for aggregated data | ACLED not in new plan core |
| **06** `sipri_match.py` | SIPRI defense exposure matching | **LOW** | Fuzzy matching logic, manual match dictionary | Only needed for optional firm-level extension |
| **07** `yahoo_volume.py` | Market cap calculation | **LOW** | Shares × price logic | Not needed for index-level study |
| **08** `gdelt_download.py` | GDELT DOC 2.0 API article counts | **MEDIUM** | GDELT API query pattern, batch date handling | **Must add source-group separation**; currently downloads only English-topic counts; needs multilingual queries + source classification |
| **09** `panel_merge.py` | Merge all sources into firm-day panel | **LOW** | Merge patterns | New plan needs index-day merge, not firm-day |
| **10** `summary_stats.py` | Summary statistics | **LOW** | Table formatting | Different variables needed |
| **11** `event_study.py` | Event study (5 events) | **NOT REUSABLE** | — | New plan is not event-study |
| **12** `panel_regressions.py` | Panel regressions M1-M4 | **NOT REUSABLE** | — | New plan is forecasting, not panel regression |
| **13** `robustness.py` | Robustness checks | **LOW** | — | Different robustness design |
| **14** `granger_did.py` | Granger causality + DiD | **NOT REUSABLE** | — | New plan is predictive, not causal |
| **15** `figures.py` | Figures | **LOW** | — | Different figures needed |

### Detailed review of high-reuse scripts

#### Script 03 — UAF Variables (HIGH reuse)

- **Weapon classification**: The `WEAPON_CLASS` dictionary contains 40+ explicit mappings from weapon model → category (drone, cruise_missile, ballistic_missile, recon_uav). This is comprehensive and well-documented.
- **`classify_model()` function**: Uses exact lookup + fuzzy keyword matching. The Cyrillic handling is valuable.
- **Aggregation**: Groups by date, sums launched/destroyed by weapon type, creates war intensity (log(1+launched)) and interception rate (destroyed/launched).
- **Issues**: 
  - Uses `time_start` as the sole date — doesn't distinguish between attack date and market information date
  - The `safe_ir()` function returns NaN for no-attack days, which may need a different treatment
  - Weapon diversity measure from the new plan is not implemented
  - No attack-surprise features

#### Script 08 — GDELT Download (MEDIUM reuse)

- **API query pattern**: Uses GDELT DOC 2.0 `timelinevol` mode for volume counts, batch processing with 3-month windows.
- **Current limitation**: Queries are English-language topic-based (e.g., `"Ukraine" AND ("war" OR "invasion")`). No source geography or language filtering.
- **For new plan**: Must be rewritten to:
  1. Use multilingual keyword dictionaries
  2. Classify sources by geography + language into Ukrainian/Russian/Western groups
  3. Save article-level records (not just daily counts)
  4. Enable deduplication

---

## 5. PDF Requirements Document Audit

**File:** `thesis_old_try/Master Thesis Coding Context and Requirements.pdf`  
**Pages:** ~11

### Key content

The PDF is the **original thesis requirements document** for the old approach. It specifies:

1. **Research question**: "Do defense stocks respond more strongly to realized conflict intensity or to media-driven geopolitical expectations?"
2. **Data**: Bloomberg firm-day panel, ACLED conflict data, GPR/GDELT media data
3. **Methodology**: Event study + panel regressions with firm×day fixed effects
4. **Key difference from new plan**: Causal framing, firm-level analysis, ACLED as primary conflict source, event studies

### Assessment

- **Not the source of truth** — the new `Master_Thesis_Research_Completion_Plan.md` supersedes it
- **No supplementary content** that isn't already covered in the new plan or the existing code
- **Can be archived** in `docs/` for reference but should not be used for decision-making
- **Recommendation**: Keep as historical reference, mark as superseded

---

## 6. Salvage Plan

### 6.1 Files to COPY to new structure

| Source Path | Destination Path | Reason | Phase Needed |
|---|---|---|---|
| `thesis_old_try/data/raw/bloomberg/WAERLST as of Jun 04 2026.xlsx` | `data/raw/bloomberg/WAERLST as of Jun 04 2026.xlsx` | Primary constituent-level financial data | Phase 1 |
| `thesis_old_try/data/raw/bloomberg/BSHIELDT as of Jun 05 2026.xlsx` | `data/raw/bloomberg/BSHIELDT as of Jun 05 2026.xlsx` | European defense constituent data | Phase 1 |
| `thesis_old_try/data/raw/bloomberg/indexes.xlsx` | `data/raw/bloomberg/indexes.xlsx` | Benchmark financial data (SPX, VIX, etc.) | Phase 1 |
| `thesis_old_try/data/raw/uaf/missile_attacks_daily.csv` | `data/raw/attacks/missile_attacks_daily.csv` | Core physical attack dataset | Phase 2 |
| `thesis_old_try/data/raw/uaf/missiles_and_uavs-selected-columns.csv` | `data/raw/attacks/missiles_and_uavs-reference.csv` | Weapon classification reference | Phase 2 |
| `thesis_old_try/data/raw/gpr/data_gpr_daily_recent.xls` | `data/raw/controls/data_gpr_daily_recent.xls` | GPR daily index for control variable | Phase 1 |
| `thesis_old_try/data/raw/gpr/data_gpr_export.xls` | `data/raw/controls/data_gpr_export.xls` | Country-specific GPR for robustness | Phase 1 |
| `thesis_old_try/data/raw/sipri/SIPRI-Top-100-2002-2024 (2).xlsx` | `data/raw/controls/SIPRI-Top-100-2002-2024.xlsx` | SIPRI data for optional firm-level extension | Phase 8+ |
| `thesis_old_try/data/raw/acled/ACLED Data_2026-06-18.csv` | `data/raw/controls/ACLED Data_2026-06-18.csv` | External reference (not core) | Reference |
| `thesis_old_try/data/raw/acled/Europe-Central-Asia_aggregated_data_up_to_week_of-2026-06-06.xlsx` | `data/raw/controls/ACLED_aggregated_weekly.xlsx` | External reference (not core) | Reference |
| `thesis_old_try/data/processed/uaf_daily.csv` | `data/interim/attacks/uaf_daily_old.csv` | Reference for validation | Phase 2 |
| `thesis_old_try/data/processed/benchmarks_daily.csv` | `data/interim/financial/benchmarks_daily_old.csv` | Reference for validation | Phase 1 |
| `thesis_old_try/data/processed/gpr_daily.csv` | `data/interim/controls/gpr_daily_old.csv` | Reference for validation | Phase 1 |
| `thesis_old_try/data/processed/gdelt_topics_daily.csv` | `data/interim/news/gdelt_old_counts.csv` | Reference only (no source separation) | Reference |
| `thesis_old_try/data/processed/firms_metadata.csv` | `data/external/firms_metadata_old.csv` | Firm universe reference | Reference |

### 6.2 Code to ADAPT (extract logic into new src/ modules)

| Source Script | Target Module | Logic to Extract |
|---|---|---|
| `scripts/03_uaf_variables.py` | `src/data/attacks.py` | Weapon classification dictionary, `classify_model()`, daily aggregation logic |
| `scripts/04_gpr_variables.py` | `src/data/financial.py` (or `src/data/controls.py`) | GPR loading, column mapping, log-transform |
| `scripts/01_bloomberg_parse.py` | `src/data/financial.py` | Excel parsing pattern, benchmark extraction (must adapt for index-level) |
| `scripts/08_gdelt_download.py` | `src/data/gdelt.py` | GDELT API batch query pattern (must add source classification) |

### 6.3 Files to DISCARD (not reusable)

| File | Reason |
|---|---|
| All scripts 02, 05, 06, 07, 09-15 | Firm-level panel methodology; not aligned with new plan |
| `data/processed/prices_daily.csv` | Firm-level; new plan needs index-level |
| `data/processed/returns_daily.csv` | Firm-level; new plan needs index-level |
| `data/processed/panel_main.csv` | Firm-level panel; old methodology |
| `data/processed/panel_full.csv` | Firm-level panel; old methodology |
| `data/processed/panel_useu.csv` | Firm-level subsample; old methodology |
| `data/processed/panel_event.csv` | Event study panel; old methodology |
| `data/processed/abnormal_returns.csv` | CAPM abnormal returns; not in new plan |
| `data/processed/car_panel.csv` | Cumulative abnormal returns; old methodology |
| `data/processed/market_model_params.csv` | CAPM params; old methodology |
| `data/processed/regression_results.csv` | Old regression results |
| `data/processed/size_daily.csv` | Firm-level; not needed for index study |
| `data/processed/acled_daily.csv` | ACLED not in new plan core |
| `data/processed/sipri_exposure.csv` | Only for optional firm-level extension |
| `output/tables/*.csv` (10 files) | Old results tables |
| `output/figures/*.png` | Old figures |
| `output/*.txt` (4 logs) | Old logs |
| `scripts/check_bruegel*.py` (6 files) | Exploratory, not part of main pipeline |
| `scripts/check_data.py` | Exploratory |
| `scripts/download_gdelt.py` | Redundant (script 08 covers this) |
| `scripts/test_gdelt.py` | Test file |

### 6.4 Files to REFERENCE (keep for documentation)

| File | Reason |
|---|---|
| `Master Thesis Coding Context and Requirements.pdf` | Original requirements; archive in `docs/` as superseded |
| `data/processed/firms_metadata.csv` | Reference for firm universe |
| `output/logs/*.txt` | Old processing logs; may help debug data issues |

---

## 7. Deletion Checklist

After salvage is complete, the following can be safely deleted from `thesis_old_try/`:

### Can delete immediately (no loss)

- `data/processed/` — all files (processed data is reproducible from raw + scripts)
- `output/` — all files (tables, figures, logs)
- `scripts/02_market_model_ar.py`
- `scripts/05_acled_variables.py`
- `scripts/06_sipri_match.py`
- `scripts/07_yahoo_volume.py`
- `scripts/09_panel_merge.py`
- `scripts/10_summary_stats.py`
- `scripts/11_event_study.py`
- `scripts/12_panel_regressions.py`
- `scripts/13_robustness.py`
- `scripts/14_granger_did.py`
- `scripts/15_figures.py`
- `scripts/check_bruegel*.py` (all 6)
- `scripts/check_data.py`
- `scripts/download_gdelt.py`
- `scripts/test_gdelt.py`

### Should keep (raw data or high-reuse code)

- `data/raw/` — all raw data files (copied to new structure, keep originals until new pipeline is validated)
- `scripts/01_bloomberg_parse.py` — reference for parsing logic
- `scripts/03_uaf_variables.py` — reference for weapon classification
- `scripts/04_gpr_variables.py` — reference for GPR processing
- `scripts/08_gdelt_download.py` — reference for GDELT API

### Can delete after new pipeline validation

- `data/raw/` (all subdirectories) — once raw files are copied to new `data/raw/` and the new pipeline produces correct outputs
- `scripts/01, 03, 04, 08` — once the logic is extracted into new `src/` modules
- The entire `thesis_old_try/` directory — after full validation

---

## 8. Unresolved Issues

| Issue | Impact | Recommendation |
|---|---|---|
| **WAERLST index-level time series not available** | New plan's primary outcome variable missing | Obtain WAERLST Index Bloomberg ticker data (likely `WAERLST Index`) separately, or reconstruct from constituent prices using index weights |
| **BSHIELDT index-level time series not available** | Robustness outcome missing | Same as WAERLST; or use SXXP (Stoxx 600) as European benchmark |
| **GDELT data has no source-group separation** | Cannot construct Ukrainian/Russian/Western news measures | Script 08 must be rewritten to classify sources by geography+language; article-level storage needed |
| **No multilingual NLP features** | Core contribution of new plan missing | Requires Phase 4 — select transformer, label sample, score articles |
| **No attack-surprise features** | Required for H1 testing | Must implement recursive expectation models (Phase 5) |
| **No narrative-gap features** | Required for H3 testing | Must implement recursive gap models (Phase 5) |
| **European defense index not selected** | Required for robustness | Must select between SXXP, BSHIELDT, or a custom European defense basket |
| **Old SIPRI matching may have full-sample bias** | If used for firm-level extension | Must redo with point-in-time matching for any predictive use |
| **UAF date assignment rules need audit** | Potential leakage | Must compare structured counts with original reports for 20+ days |
| **Bloomberg data: price or total-return?** | Affects return calculation | Must verify against Bloomberg field codes; check if dividends are included |

---

## 9. Recommended Next Action

1. **Copy raw data files** to the new `data/raw/` structure as specified in Section 6.1.
2. **Extract weapon classification dictionary** from `scripts/03_uaf_variables.py` into `src/data/attacks.py`.
3. **Begin Phase 1** (Financial Data Audit) using the Bloomberg constituent data and benchmarks — this will determine whether WAERLST index-level data must be obtained separately or can be reconstructed.
4. **Do not delete `thesis_old_try/`** until the new pipeline produces validated outputs for the same date ranges as the old processed data.
