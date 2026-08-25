# Reproducing the thesis end to end

Every number in the draft comes from a committed script. This is the order to
run them in, what each needs, and what it costs.

**Two things are not reproducible from this repository alone**, and both are
stated in the thesis rather than hidden:

- **The Bloomberg index series** (`WAERLST`, `BSHIELDT`, 2020–2026). Proprietary,
  gitignored, and held in one place — mirrored to
  `gdrive:WarSignalsThesis_Data/data/raw/bloomberg/`. Everything that uses them
  degrades gracefully to the free equity spine, at the cost of the referee
  comparison in Chapter 3.
- **The firm-level constituent panel and SIPRI exposure data.** These no longer
  exist anywhere. No cross-sectional analysis is possible, which Chapter 3
  records as a limitation rather than a design choice.

---

## Prerequisites

```bash
source .venv/bin/activate          # from the project root
pip install -r requirements.txt
pip install google-cloud-bigquery db-dtypes   # for the ingest only
```

BigQuery needs a service-account key with the **BigQuery Job User** role at
`~/.config/gcp/warsignals-bq.json`, project `warsignals-thesis`. See
[`environment_setup.md`](environment_setup.md) §3.2. Set a 200 GB/day quota:
roles bound blast radius, quotas bound spend, and they are independent.

Everything except the ingest runs with no credential and no cost.

## 1. Data collection

```bash
# run from the repository root
python scripts/build_spine.py                 # GPR + FRED, free
python scripts/build_equity_spine.py          # Yahoo, free; runs the basket validation
python scripts/ingest_gdelt.py --preset full             # ~380 GB scanned
python scripts/ingest_gdelt.py --preset holdout         # ~90 GB
python scripts/ingest_gdelt.py --preset threat-act      # ~454 GB
python scripts/ingest_gdelt.py --preset threat-act-fill # ~706 GB
python scripts/run_classifier_sensitivity.py            # ~380 GB, five labellings in one scan
```

Add `--dry-run` to any ingest to price it without running it. The full wave is
roughly **1.6 TB** for the four ingest presets, or **2.0 TB** including the
sensitivity scan, which overruns BigQuery's 1 TB/month free tier — budget a few
dollars if you run them all in one calendar month. The two `threat-act` presets
write to the same file and together cover all 4,027 days; the split exists
because the `Themes` field they read scans at roughly four times the cost of the
`Locations` field the other presets use, and the episode windows were collected
first.

The ingest is chunked purely as a cost control. Results are identical to a
single query over the same span.

**Re-running an ingest genuinely re-ingests.** Existing rows are merged with
freshly queried ones and the fresh row wins on a collision. This was not always
true: the merge kept the *first* row, and since existing data is concatenated
first, every re-query was silently resolved in favour of the stale copy. The
threat/act table survived a 454 GB re-run byte-identical after the outlet
register had been corrected — the query ran, the bill was paid, the result was
discarded, and Gate 3 went on reporting numbers from the old register.
`tests/test_register_and_exposure.py::TestIngestMerge` is the regression test.

## 2. Analysis

**Confirmatory** — the pre-registered gates and the headline results:

```bash
python scripts/run_gates.py            # Gate 1 validation + Gate 2 horse race
python scripts/run_gate3.py            # threat/act structure, pre-registered
python scripts/run_gate4_gas.py        # European gas, pre-registered
python scripts/run_gate5_escalation.py # escalation on held-out days, pre-registered
python scripts/run_forecast_null.py    # 50 OOS specs + the simulated power curve
python scripts/analyse_wedge.py        # censorship wedge, fixed panel (needs BigQuery)
python scripts/plot_stylized_facts.py  # Figures 1 and 2
```

**Diagnostic and exploratory** — the evidence behind Chapters 4, 5, 6 and 8.
Chapter 8 is a retraction record, so the work that produced each retracted
finding has to be runnable or the chapter cannot be checked:

```bash
python scripts/verify_corpus.py           # Ch 3-4: coverage, column costs, outlet register
python scripts/run_episode_analysis.py    # Ch 5 §5.4: episode table + per-episode tests
python scripts/compare_news_timing.py     # Ch 6: same-day vs lagged alignment
python scripts/diagnose_market_control.py # Ch 8 §8.1: THE retraction evidence
python scripts/audit_gate3.py             # Ch 8 §8.2: strict rule + OOS sign test
python scripts/diagnose_gas.py            # Ch 8 §8.4: asset scan + adversarial tests
python scripts/explore_escalation.py      # Ch 8 §8.5: split-half + persistence diagnostic
python scripts/run_break_tests.py         # Ch 5 §5.4: Chow + supremum-Wald breaks
python scripts/run_register_audit.py      # Ch 4 §4.5: outlet precision against Wikidata
python scripts/run_exposure_gradient.py   # Ch 8 §8.7: SIPRI firm-level exposure gradient
python scripts/run_classifier_sensitivity.py  # Ch 4 §4.5: Gate 2 under five classification rules
```

Two of those need a note.

`run_register_audit.py` reads Wikidata over the network and takes several
minutes. Resolutions are **pinned** to a committed QID map, so a re-run
reproduces the table exactly; without the pin it would not, because Wikidata's
name-search ranking is unstable enough to move measured precision between runs of
identical code. `--repin` re-resolves every outlet from scratch and rewrites the
map, and is the right thing to run when the register changes — it takes far
longer, because it examines every candidate rather than the first plausible one.

`run_exposure_gradient.py` needs `data/raw/sipri/sipri_top100.xlsx`, which is not
in the repository. Download the SIPRI Arms Industry Database Top-100 workbook
from sipri.org and put it there; the parser reads every year sheet it finds.

`run_classifier_sensitivity.py` re-labels the corpus five ways and re-runs Gate 2
under each. It scans **380 GB** on its first run — the same as one ingest, because
the rules differ in how they label an article and not in which articles they
read, so a single scan carries all five labellings. The result is committed as
`data/interim/gdelt_ecosystems_variants.parquet`; pass **`--no-ingest`** to
re-run the regressions against it without querying BigQuery again.

`diagnose_market_control.py` is the one to run first if you only run one. It
reproduces the reversal that retracted the threat channel — the same regression
under SP500 and STOXX 600 — and the mechanism behind it.

Two of these need BigQuery (`verify_corpus.py`, `analyse_wedge.py`) because they
query at article and outlet level, which the committed daily aggregates cannot
answer. The rest run offline against the interim parquets.

`run_forecast_null.py` is the slow one — the power curve simulates 150 paths per
grid point, each re-running the expanding-window forecast. Reduce with
`--n-sims` if you only want the point estimates.

`gpr_regime_preview.py` is kept but produces a **retracted** result. It is in the
repository because Chapter 8 documents the retraction; do not cite its output.

## 3. Verification

```bash
python -m pytest tests/ -q     # 125 tests, all offline
```

The suite needs neither the network nor the gitignored data: parsers are split
from fetchers throughout, and the estimators are tested against synthetic series
with a planted coefficient.

## 4. Building the document

```bash
cd thesis
./build.sh tex        # thesis.tex, for Overleaf
./build.sh pdf        # thesis.pdf, needs a local LaTeX engine
```

`tex` and `docx` are **verified** with pandoc 3.1.11: they build clean from the
chapters, and the tex output carries 9 chapters, 3 figures, 54 tables and all 16
bibliography entries. `pdf` is the one target still unverified, because it needs
a LaTeX engine and none is installed on the machine the thesis was written on —
build `tex` and upload to Overleaf if you do not have one either.

## What each analysis writes

| script | outputs |
|---|---|
| `build_spine.py` | `data/interim/spine_macro.parquet`, `outputs/tables/spine_coverage.csv` |
| `build_equity_spine.py` | `data/interim/spine_full.parquet`, `outputs/tables/basket_validation.csv` |
| `ingest_gdelt.py` | `data/interim/gdelt_ecosystems_daily.parquet`, `gdelt_threat_act_daily.parquet`, `gdelt_ecosystems_holdout.parquet` |
| `run_gates.py` | `outputs/tables/gate1_ecosystems.csv`, `gate1_collinearity.csv`, `gate1_gpr_levels.csv`, `gate2_horse_race.csv` |
| `run_gate3.py` | `outputs/tables/gate3_threat_act.csv` |
| `run_gate4_gas.py` | `outputs/tables/gate4_gas.csv`, `gate4_placebos.csv` |
| `run_gate5_escalation.py` | `outputs/tables/gate5_escalation.csv` |
| `run_forecast_null.py` | `outputs/tables/forecast_null.csv`, `forecast_power_curve.csv` |
| `analyse_wedge.py` | `outputs/tables/wedge_fixed_panel.csv`, `wedge_summary.csv` |
| `plot_stylized_facts.py` | `outputs/figures/fig1_attention_full_sample.png`, `fig2_tone_full_sample.png` |
| `verify_corpus.py` | `outputs/tables/corpus_span.csv`, `corpus_top_outlets.csv`, `corpus_column_costs.csv` |
| `run_episode_analysis.py` | `outputs/tables/episodes.csv`, `episode_threat_act.csv`, `episode_pooled.csv` |
| `compare_news_timing.py` | `outputs/tables/gate2_news_timing.csv` |
| `diagnose_market_control.py` | `outputs/tables/market_control_{reversal,mechanism,survives}.csv` |
| `audit_gate3.py` | `outputs/tables/gate3_oos_signs.csv`, `gate3_sign_consistency.csv` |
| `diagnose_gas.py` | `outputs/tables/gas_{asset_scan,controls,placebos}.csv` |
| `explore_escalation.py` | `outputs/tables/escalation_{levels_vs_changes,split_half}.csv` |
| `run_break_tests.py` | `outputs/tables/structural_breaks.csv` |
| `run_register_audit.py` | `outputs/tables/register_audit.csv`, `register_audit_summary.csv` |
| `run_exposure_gradient.py` | `outputs/tables/exposure_gradient.csv`, `exposure_gradient_bh.csv`, `sipri_exposure.csv` |
| `run_classifier_sensitivity.py` | `data/interim/gdelt_ecosystems_variants.parquet`, `outputs/tables/classifier_sensitivity.csv`, `classifier_sensitivity_cells.csv` |

## What reproduces, and what deliberately does not

**The committed data and the chapters agree.** Every parquet in `data/interim/`
was regenerated on the final outlet register, and every table in
`outputs/tables/` was regenerated from those parquets, so running the analysis
scripts on this checkout reproduces the figures the chapters quote. That was not
true for most of the project's life, and the way it failed is worth knowing:

- The ecosystem tables lagged the register by one fix, so the chapters quoted
  RU_INDEP and WEST figures from a register that had `dw.com` in the wrong block.
- The threat/act table lagged it by **two**, and silently. Re-ingesting it looked
  like it worked — the query ran and 454 GB was scanned — but the merge kept the
  stale row on every collision, so Gate 3 went on reporting pre-fix numbers. That
  bug is fixed and has a regression test; see §1.

**The `pdf` build target and one raw input do not reproduce here.** `pdf` needs a
LaTeX engine this machine lacks, and `run_exposure_gradient.py` needs the SIPRI
workbook, which is not redistributable through this repository.

**Re-fetching the price data will move the numbers slightly, so do not.**
`build_equity_spine.py` pulls adjusted closes, and adjusted closes are revised
retroactively for splits and dividends. The committed `spine_full.parquet` is
what every reported figure was computed on. Re-running it is only correct if you
intend to re-derive the whole chapter, not to check a number.

**A pre-registered result reports the data it was run on.** Where a gate's
recorded verdict was formed on a smaller corpus, that verdict stands as the
record of what was pre-registered, and the current table stands as what the same
test says now. Re-estimating on later-arriving data and reporting the better
answer is exactly the failure mode Gate 3 documents, where adding a held-out
window turned seven survivors into two and a PASS into a FAIL.

## Added after the first pass

Two scripts close gaps against commitments in
[`supervisor_response_matrix.md`](supervisor_response_matrix.md) that the first
pass left unimplemented:

```bash
python scripts/run_break_tests.py      # Ch 5 §5.4: Chow + supremum-Wald breaks
python scripts/run_forecast_null.py    # Ch 7 §7.5 now also runs combination,
                                       # economic value and the Model Confidence Set
```

`run_break_tests.py` bootstraps the supremum statistic, so it is the slowest
offline script — about a minute at 500 draws. The scan uses a closed form for the
intercept-only case; supplying a regressor falls back to refitting and is
markedly slower.

One item promised in the response matrix remains unimplemented: **HAR-RV-X**.
Volatility was dropped as an outcome when the only volatility result in the
project was retracted (Chapter 8 §8.1), so there is no volatility arm for it to
serve. Chapter 8 records this as a scope reduction rather than leaving the
promise silently unmet.
