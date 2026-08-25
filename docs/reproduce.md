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
python scripts/ingest_gdelt.py --preset full        # ~380 GB scanned
python scripts/ingest_gdelt.py --preset threat-act  # ~310 GB
python scripts/ingest_gdelt.py --preset holdout     # ~90 GB
```

Add `--dry-run` to any ingest to price it without running it. Total across all
three presets is roughly 800 GB, inside BigQuery's 1 TB/month free tier — but
only just, so a re-run in the same calendar month may cost a few dollars.

The ingest is chunked purely as a cost control. Results are identical to a
single query over the same span.

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
```

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
python -m pytest tests/ -q     # 85 tests, all offline
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

**Not tested** — neither pandoc nor LaTeX is installed on the machine the thesis
was written on. `build.sh` documents its likely first-run failures at the bottom
of the file.

## What each analysis writes

| script | outputs |
|---|---|
| `build_spine.py` | `data/interim/spine_macro.parquet`, `outputs/tables/spine_coverage.csv` |
| `build_equity_spine.py` | `data/interim/spine_full.parquet`, `outputs/tables/basket_validation.csv` |
| `ingest_gdelt.py` | `data/interim/gdelt_ecosystems_daily.parquet`, `gdelt_threat_act_daily.parquet`, `gdelt_ecosystems_holdout.parquet` |
| `run_gates.py` | `outputs/tables/gate1_ecosystems.csv`, `gate1_collinearity.csv`, `gate2_horse_race.csv` |
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

## Where re-running gives different numbers, and why that is correct

Two scripts will not reproduce the chapters exactly, because the corpus grew
after those results were recorded:

- **`compare_news_timing.py`** gives 3 same-day BH survivors where Chapter 6
  reports 2. Gate 2 ran on the 1,605-day ingest; the corpus is now 4,027 days.
  The lagged count is 0 either way, which is the specification the chapter
  treats as primary.
- **`analyse_wedge.py`** gives five independent outlets and p=0.323 where the
  pre-correction run gave six and p=0.151, because `dw.com` has since been moved
  out of the Russian-independent register. Chapters 5 and 8 quote the corrected
  figures.

Neither is a discrepancy to fix. A pre-registered result reports the data it was
run on, not the data that exists later — re-estimating on later-arriving data is
exactly the failure mode Gate 3 documents, where adding a held-out window turned
seven survivors into two and a PASS into a FAIL.

## A caveat on re-running

The committed ecosystem parquets were built **before** `dw.com` was corrected
from Russian-independent to Western in the outlet register. Re-running
`ingest_gdelt.py` regenerates them with the corrected classifier, which will
change RU_INDEP and WEST slightly. It does **not** touch the state-versus-Ukraine
contrast the thesis actually claims, since neither ecosystem is involved.

`analyse_wedge.py` already reflects the corrected register: it gives five
independent outlets and p = 0.323, against six and p = 0.151 before the fix.
Chapters 5 and 8 quote the corrected figures.
