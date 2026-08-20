# Phase 1 — where the long-sample data actually comes from

**Date:** 2026-08-20 · **Status:** macro half built; equity half blocked on a choice

Every claim below was tested from a cloud session, not assumed.

---

## 1. What works with no credentials

| Source | Endpoint | Coverage | Verdict |
|---|---|---|---|
| **GPR** (Caldara & Iacoviello) | `matteoiacoviello.com/gpr_files/data_gpr_daily_recent.xls` | daily **1985-01-01 → 2026-08-17**, 15,204 rows, `GPRD` / `GPRD_ACT` / `GPRD_THREAT` | ✅ works |
| **FRED** | `fred.stlouisfed.org/graph/fredgraph.csv?id=…` | daily 2015 → now, no API key | ✅ works |

FRED series used: `VIXCLS` (vix), `DCOILBRENTEU` (brent), `DEXUSEU` (usd_eur),
`DGS10` (ust10y), `DTWEXBGS` (usd_broad).

**Built and committed:** `data/interim/spine_macro.parquet` — 4,151 calendar
days, 2015-02-18 → 2026-06-30, 18 columns, **100% coverage** on GPR and all five
FRED controls. Reproduce with `cd thesis_v2 && python scripts/phase1_build_spine.py`.

## 2. What does not work from here

| Source | Result |
|---|---|
| **Yahoo Finance** (`yfinance`, and the raw chart API) | `429 Too Many Requests`. The cloud session's shared egress IP is rate-limited by Yahoo. Not a fixable configuration issue. |
| **Stooq** | Serves a JavaScript proof-of-work challenge instead of CSV. |
| **FRED, for equities** | Has no individual stocks, no STOXX, and its `SP500` series is truncated to a rolling 10 years (starts ~2016). |

So the **equity half of the spine cannot be built from a cloud session** without
either a keyed vendor or a file produced elsewhere.

## 3. The equity gap, and three ways to close it

What is needed: daily OHLC for the defence names, the ETFs, and the regional
benchmarks (SPX, SXXP, MSCI World), 2015 → 2026.

### Option A — use the Bloomberg data that already exists (recommended first step)

`WAERLST Index.xlsx` and `BSHIELDT Index.xlsx` on Drive already cover
**2020-01-01 → 2026-06-30**, with constituent-level prices for 118 + 36 firms.

This is worth stating plainly: **that window already contains February 2022.**
Relative to the reviewed paper it roughly doubles the sample (~920 → ~1,650
trading days) and puts the invasion re-rating inside it — which is the larger
part of what supervisor comment #1 asks for, using data already collected.

Needs: a Drive sync from a laptop, then commit the derived daily series.

### Option B — a free API key (closes 2015–2019)

Twelve Data (800 requests/day free) or Tiingo (free tier, long EOD history).
One key as an environment variable, and the full 2015–2026 window builds from a
cloud session with no further manual steps. This is the only option that makes
the equity pipeline reproducible from here.

### Option C — one Colab run

Yahoo works fine from a Colab or residential IP. A notebook pulls the tickers
with `yfinance` and writes CSVs to the repo. Free and quick, but the pipeline
then depends on a human running a notebook, and Yahoo's history is
survivorship-biased for delisted names.

**Recommendation: A now, B alongside it.** Option A restores the invasion to the
sample immediately using data already paid for; Option B extends to 2015 and
makes the whole thing reproducible. They are not exclusive — the 2020–2026
overlap is exactly the window needed to validate the free basket against
Bloomberg, which is the check v1's *reconstructed* indices failed at ρ = 0.15.

## 4. What the macro spine already shows

Face-validity checks on the built spine, all consistent with the regime design:

**Mean GPR by regime**

| Regime | GPR | ACT | THREAT | VIX |
|---|---|---|---|---|
| pre_war (2015-02 → 2021-10) | 93.1 | 77.3 | 105.2 | 17.6 |
| buildup (2021-11 → 2022-02-23) | 119.3 | 54.9 | **174.0** | 21.9 |
| invasion (2022-02-24 → 2022-09-28) | 167.5 | 143.7 | 206.4 | 26.0 |
| attrition (2022-09-29 →) | 140.8 | 140.7 | 153.8 | 17.9 |

**The buildup window behaves exactly as the design predicts.** Its
threat-to-act ratio is **3.17**, against 1.36 pre-war, 1.44 during the invasion
and 1.09 in attrition. It is a period of intense anticipation with almost no
realized geopolitical acts — close to a natural experiment for the
threat-versus-act question, and it sits entirely outside the reviewed sample.

**The invasion is visible day by day.** GPR runs 152 → 279 → 431 over
21–23 February 2022, driven almost entirely by THREAT (244 → 439 → 693) while
ACT barely moves (135 → 122 → 183). ACT only jumps on 26 February, to 363.
Anticipation first, realization after.

**And this is the quantitative case for the sample extension.** In the attrition
regime — the whole of the v1 sample — the threat-to-act ratio is 1.09 and the
two series correlate at 0.59. They are nearly the same variable there, which is
why v1 could not tell them apart. The variation needed to separate them lives in
the buildup and invasion windows, both of which were outside the sample.

## 5. Next

1. Decide the equity route (§3). Option A needs a Drive sync; Option B needs one
   free API key as an environment variable.
2. Attach the equity half: returns, realized volatility (Parkinson/Garman-Klass
   from OHLC, not just squared close-to-close), and regional market-model
   residuals.
3. Then Phase 2, which needs the BigQuery service account
   (`environment_setup.md` §3.2).
