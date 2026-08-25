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
pip install -r thesis_v2/requirements.txt
pip install google-cloud-bigquery db-dtypes   # for the ingest only
```

BigQuery needs a service-account key with the **BigQuery Job User** role at
`~/.config/gcp/warsignals-bq.json`, project `warsignals-thesis`. See
[`environment_setup.md`](environment_setup.md) §3.2. Set a 200 GB/day quota:
roles bound blast radius, quotas bound spend, and they are independent.

Everything except the ingest runs with no credential and no cost.

## 1. Data collection

```bash
cd thesis_v2
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

```bash
python scripts/run_gates.py            # Gate 1 validation + Gate 2 horse race
python scripts/run_gate3.py            # threat/act structure, pre-registered
python scripts/run_gate4_gas.py        # European gas, pre-registered
python scripts/run_gate5_escalation.py # escalation on held-out days, pre-registered
python scripts/run_forecast_null.py    # 50 OOS specs + the simulated power curve
python scripts/analyse_wedge.py        # censorship wedge, fixed outlet panel (needs BigQuery)
python scripts/plot_stylized_facts.py  # Figures 1 and 2
```

`run_forecast_null.py` is the slow one — the power curve simulates 150 paths per
grid point, each re-running the expanding-window forecast. Reduce with
`--n-sims` if you only want the point estimates.

`gpr_regime_preview.py` is kept but produces a **retracted** result. It is in the
repository because Chapter 8 documents the retraction; do not cite its output.

## 3. Verification

```bash
cd thesis_v2 && python -m pytest tests/ -q     # 85 tests, all offline
```

The suite needs neither the network nor the gitignored data: parsers are split
from fetchers throughout, and the estimators are tested against synthetic series
with a planted coefficient.

## 4. Building the document

```bash
cd thesis_v2/thesis
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

## A caveat on re-running

The committed ecosystem parquets were built **before** `dw.com` was corrected
from Russian-independent to Western in the outlet register. Re-running
`ingest_gdelt.py` regenerates them with the corrected classifier, which will
change RU_INDEP and WEST slightly. It does **not** touch the state-versus-Ukraine
contrast the thesis actually claims, since neither ecosystem is involved.

`analyse_wedge.py` already reflects the corrected register: it gives five
independent outlets and p = 0.323, against six and p = 0.151 before the fix.
Chapters 5 and 8 quote the corrected figures.
