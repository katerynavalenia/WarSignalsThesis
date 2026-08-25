# v1 — Archived Draft

**Status: superseded. Do not build on this question or edit these files.**
Kept as a historical record and as a source of reusable data/code for v2.

## What v1 was

**Title:** *War Signals and Defense Equity Risk: Physical Air-Attack Intensity
versus Multilingual News Narratives*
**Question:** Do unexpected changes in Russian air-attack intensity and
multilingual news narratives provide *incremental out-of-sample predictive
information* for defense-equity returns and volatility, beyond financial
controls?
**Design:** Index-level (ITA → later real WAERLST/BSHIELDT), daily,
expanding-window OOS forecasting horse race (F/P/N/PN/PNG information sets),
econometric baselines (AR/OLS/Ridge/GARCH) + XGBoost + SHAP.

## What v1 found

A **rigorous null**, confirmed from multiple independent angles (naive OLS,
regularized Ridge with proper standardization, Clark–West out-of-sample
tests, in-sample and out-of-sample, on both the ITA proxy and the real
Bloomberg WAERLST/BSHIELDT indices): neither physical attack intensity nor
multilingual news narratives improve return or volatility forecasts beyond
a financial baseline (VIX, lagged volatility, the war-regime trend). Full
reasoning and numbers: [`supervisor_audit.md`](supervisor_audit.md).

This is not a coding failure — the null is economically expected (defense
primes are priced on multi-year procurement, not daily tactics) and the
plan's own §12.1/§23 explicitly pre-authorized a null result. But it is a
**thin** contribution on its own, which motivated the v2 pivot.

## Why v2 exists

`supervisor_audit.md` §4.1 lays out three options after the null: (A) write
v1 up as a null, (B) pivot the dependent variable/design to where a
response is more likely to exist, (C) change topic entirely. Follow-up
testing (see the chat-derived findings folded into
[`../v2/research_plan.md`](../v2/research_plan.md)) showed that a
**firm-level, contemporaneous-response** design — not index-level forecasting
— finds a robust, significant result: firm-level idiosyncratic volatility
responds to realized attack intensity but not to media attention. That
became v2.

## Reading order (if you need v1 context)

1. [`supervisor_audit.md`](supervisor_audit.md) — the independent scientific
   review that triggered the pivot; contains the decisive OOS tests.
2. [`../../thesis_v1/README.md`](../../thesis_v1/README.md) § "Current phase" —
   phase-by-phase status as of the pivot (Phases 0–7 substantially complete,
   8–10 not started). The former `project_status.md` was removed in the
   2026-08-16 context cleanup; restore it from the `pre-context-cleanup` tag
   if the fuller narrative is needed.
3. [`phase1_financial_audit.md`](phase1_financial_audit.md) through
   [`phase7_audit.md`](phase7_audit.md) — per-phase technical audits.
4. [`new_scope_plan.md`](new_scope_plan.md) — an intermediate, superseded
   pivot plan (kept real indices, still forecasting-framed); superseded
   again by v2's response framing.
5. [`thesis_old_try_audit.md`](thesis_old_try_audit.md) — audit of an even
   earlier attempt, whose raw data (GPR, SIPRI) v2 reuses.

## What v2 reuses from v1 (do not re-download)

All paths below are relative to `thesis_v1/`:

| Asset | Path | Reused for |
|---|---|---|
| Real Bloomberg indices | `data/raw/bloomberg/{WAERLST,BSHIELDT} Index.xlsx` | firm/index returns |
| Cleaned financial table | `data/processed/financial/financial_daily.parquet` | controls (VIX, benchmarks) |
| Attack daily table | `data/processed/attacks/attack_daily.parquet` | realized-intensity channel |
| GDELT daily aggregates | `data/processed/news/news_daily_enriched.parquet`, `news_query_group_pivot.parquet` | media-attention + narrative-gap channels, per UA/RU/Western/Other |
| WAERLST/BSHIELDT constituents | `data/interim/financial/{waerlst,bshieldt}_constituents_{long,wide}.parquet` | firm-level panel (118 + 36 firms) |
| Firm metadata | `data/external/firms_metadata_old.csv` | region, country, market cap |
| GPR daily index (new to v2) | `thesis_old_try/data/raw/gpr/data_gpr_daily_recent.xls` | expectations channel (GPRD_ACT vs GPRD_THREAT) |
| SIPRI Top-100 (new to v2) | `thesis_old_try/data/raw/sipri/SIPRI-Top-100-2002-2024 (2).xlsx` | defense-revenue exposure |
| Old GPR parsing script | `thesis_old_try/scripts/04_gpr_variables.py` | reference for parsing GPR |

The multi-GB raw GDELT article corpus and the ML/GARCH-X model code are
**not** needed for v2's core design; they stay archived in `thesis_v1/`
and are cited only if v2 later needs to re-derive a GDELT feature.
