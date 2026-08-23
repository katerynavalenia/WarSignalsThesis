# Findings status — what is live, what is retracted

**Read this before citing any number from any document in `docs/v3/`.**

Five plausible positives were produced and retracted in this project. The
documents that reported them are kept unedited, because the sequence is part of
the contribution — but that means several files state, in their own voice,
results that no longer hold. This page is the authority on which is which.

**Last updated:** 2026-08-23

---

## Retracted — do not cite

| # | claim | where it is stated | what killed it |
|---|---|---|---|
| 1 | GPR_THREAT raises European defence volatility (p<0.001) | `../v2/research_plan.md` §6.4 | the correct regional market control |
| 2 | Threat shocks move defence returns in the build-up (p=0.0001) | [`gpr_regime_preview.md`](gpr_regime_preview.md) — **banner added** | SPX → SXXP; p becomes 0.843 |
| 3 | Local media's threat/act structure is priced (7 BH survivors) | [`gate3_results.md`](gate3_results.md) §"pass that evaporated" | adding the held-out window; 7 survivors → 2, verdict FAIL |
| 4 | Local perception is priced in European gas (p=0.0005) | [`gate4_preregistration.md`](gate4_preregistration.md) §exploratory | pre-registered replication, n 81 → 222, p → 0.100 |
| 5 | Local media anticipate realized escalation (both halves significant) | [`gate5_preregistration.md`](gate5_preregistration.md) §exploratory | pre-registered held-out sample, p → 0.16 |
| 6 | The state-vs-**independent** censorship wedge | [`gate1_gate2_results.md`](gate1_gate2_results.md) §5 — **banner added** | fixed outlet panel, p=0.151; plus a register error (`dw.com`) |

Each was significant at conventional levels when found. Each had a plausible
mechanism. The failure modes are all different — two omitted-variable problems,
one truncated sample, one small sample, one in-sample split that did not
generalise, one composition change — which is why the sequence is worth
reporting rather than hiding.

## Live — safe to cite

| claim | number | source |
|---|---|---|
| v1's indicators were English-only and topic-classified | 7 `.ru` / 21 `.ua` of 60,690; 88.6% by country mentioned | [`gdelt_measurement_diagnosis.md`](gdelt_measurement_diagnosis.md) |
| Ecosystems are genuinely distinct | max pairwise ρ 0.673; UA↔EN_GLOBAL **0.05** | [`gate1_gate2_results.md`](gate1_gate2_results.md) §4 |
| Indices track published GPR when GPR is about Ukraine | 0.866 WEST / 0.884 EN_GLOBAL in levels; 0.08 in 2017-19 | §4 |
| Russian **state** media's tone did not move at the invasion | +0.02 aggregate; **−0.05 on a fixed 24-outlet panel** | §5 + [`gate3_results.md`](gate3_results.md) addendum |
| Ukrainian media's tone fell sharply | −1.66 | §5 |
| Local perception is not priced in defence equities | Gates 2 and 3, positive controls pass | `gate2`/`gate3_results.md` |
| Local perception is not priced in European gas | Gate 4, all four conditions fail | [`gate4_results.md`](gate4_results.md) |
| Local perception does not anticipate escalation out of sample | Gate 5, p=0.16 / 0.30 | [`gate5_results.md`](gate5_results.md) |
| No out-of-sample return predictability | 0 of 50 Clark–West rejections | `outputs/tables/forecast_null.csv` |
| Power bound on that null | **R²_OS 1.0% detectable at 80% power**, 0.5% at 56% | `outputs/tables/forecast_power_curve.csv` |
| Threat *is* priced market-wide in Europe | SXXP loads +0.474, p<0.0001 | [`gate1_gate2_results.md`](gate1_gate2_results.md) §6b |
| Sample coverage | **2015-02-18 → 2026-05-20, 4,027 days, 98% of calendar** | ingest logs |

## Provisional — cite with the caveat attached

- **Ecosystem classification precision.** The hand-labelled audit was never run.
  `dw.com` was found misclassified by a robustness run rather than by validation,
  which is the concrete argument for completing it.
- **Committed ecosystem tables predate the `dw.com` fix.** The register is
  corrected in `ecosystems.py`; the parquet files are not regenerated. This
  affects RU_INDEP only, and therefore does not touch the state-vs-Ukraine
  contrast the thesis actually claims.

## Known-stale statements in otherwise-valid documents

| document | stale claim | correction |
|---|---|---|
| [`data_sources.md`](data_sources.md) §2–3 | the equity half cannot be built without a vendor key | true of cloud sessions only; built free from a residential IP — **banner added** |
| [`research_plan_v3.md`](research_plan_v3.md) §9 | odds table presented as live priors | every row now settled — **banner added** |
| [`gate1_gate2_results.md`](gate1_gate2_results.md) §8 | "1,605 days ingested, not 4,151" | correct for that gate; coverage is now 4,027 days |
| [`project_status.md`](project_status.md) | next actions | superseded by Gates 3–5 |

Gate documents describing the sample *they* were run on are correct as written
and are not stale. A gate result must report the data it used, not the data that
exists now — re-estimating a pre-registered test on later-arriving data is the
failure mode Gate 3 documents.

## Rule

Any new document that reports a result must either appear in the **Live** table
here or carry its own banner. A finding that is not in this file has not been
checked against the retractions.
