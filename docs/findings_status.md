# Findings status — what is live, what is retracted

**Read this before citing any number from any document in `docs/`.**

Five plausible positives were produced and retracted in this project. The
documents that reported them are kept unedited, because the sequence is part of
the contribution — but that means several files state, in their own voice,
results that no longer hold. This page is the authority on which is which.

**Last updated:** 2026-08-23

---

## Retracted — do not cite

| # | claim | where it is stated | what killed it |
|---|---|---|---|
| 1 | GPR_THREAT raises European defence volatility (p<0.001) | [`v2 §6.4`](../archive/v2_response_pivot/research_plan.md) | the correct regional market control |
| 2 | Threat shocks move defence returns in the build-up (p=0.0001) | [`gpr_regime_preview.md`](gpr_regime_preview.md) — **banner added** | SPX → SXXP; p becomes 0.843 |
| 3 | Local media's threat/act structure is priced (7 BH survivors) | [`gate3_results.md`](gate3_results.md) §"pass that evaporated" | adding the held-out window; 7 survivors → 2, verdict FAIL |
| 4 | Local perception is priced in European gas (p=0.0005) | [`gate4_preregistration.md`](gate4_preregistration.md) §exploratory | pre-registered replication, n 81 → 222, p → 0.399 |
| 5 | Local media anticipate realized escalation (both halves significant) | [`gate5_preregistration.md`](gate5_preregistration.md) §exploratory | pre-registered held-out sample, p → 0.16 |
| 6 | The state-vs-**independent** censorship wedge | [`gate1_gate2_results.md`](gate1_gate2_results.md) §5 — **banner added** | fixed outlet panel. **p=0.561 with the fully corrected register** (four outlets, −0.17); p=0.323 after the `dw.com` fix alone (five, −0.22); p=0.151 before it (six, −0.31). Each register correction moves it *further* from significance |

Each was significant at conventional levels when found. Each had a plausible
mechanism. The failure modes are all different — two omitted-variable problems,
one truncated sample, one small sample, one in-sample split that did not
generalise, one composition change — which is why the sequence is worth
reporting rather than hiding.

## Live — safe to cite

| claim | number | source |
|---|---|---|
| v1's indicators were English-only and topic-classified | 7 `.ru` / 21 `.ua` of 60,690; 88.6% by country mentioned | [`gdelt_measurement_diagnosis.md`](gdelt_measurement_diagnosis.md) |
| Ecosystems are genuinely distinct | max pairwise ρ 0.602; UA↔EN_GLOBAL **0.02** | [`gate1_gate2_results.md`](gate1_gate2_results.md) §4 |
| Indices track published GPR when GPR is about Ukraine | 0.866 WEST / 0.884 EN_GLOBAL in levels; 0.08 in 2017-19 | §4 |
| Russian **state** media's tone did not move at the invasion | +0.02 aggregate; **−0.05 on a fixed 24-outlet panel** | §5 + [`gate3_results.md`](gate3_results.md) addendum |
| Ukrainian media's tone fell sharply | −1.66 | §5 |
| Local perception is not priced in defence equities | Gates 2 and 3. Control survives BH in Gate 3 (2/31, min p=0.00016); in Gate 2 it does not survive anywhere, and sensitivity rests on the local block's own same-day detections (7/31) collapsing to 1/31 when lagged | `gate2`/`gate3_results.md` |
| Local perception is not priced in European gas | Gate 4, all four conditions fail | [`gate4_results.md`](gate4_results.md) |
| Local perception does not anticipate escalation out of sample | Gate 5, p=0.21 / 0.23 | [`gate5_results.md`](gate5_results.md) |
| No out-of-sample return predictability | 0 of 50 Clark–West rejections | `outputs/tables/forecast_null.csv` |
| Power bound on that null | **R²_OS 0.5% detectable at 82% power**, 0.2% at 43%, on 1,855 OOS days | `outputs/tables/forecast_power_curve.csv` |
| Threat *is* priced market-wide in Europe **during the build-up and invasion** | SXXP loads +0.474, p<0.0001 on that window; +0.028, p=0.15 on the full sample | [`gate1_gate2_results.md`](gate1_gate2_results.md) §6b |
| Sample coverage | **2015-02-18 → 2026-05-20, 4,027 days, 98% of calendar**; ~3× the reviewed version on matched units (2,837 trading days vs 931) | ingest logs |
| Outlet register precision, audited against Wikidata | **0.955** on 66 of 84 verifiable outlets; RU_STATE, WEST and UA all 1.000; all three disagreements are exile newsrooms | `outputs/tables/register_audit.csv`, thesis §4.6 |
| The null does not depend on the classification rule | Gate 2 survivors 1–2 of 31 under all five rules, primary alignment | `outputs/tables/classifier_sensitivity.csv` |
| A language-first classifier cannot represent the state/independent split | `language_first` produces no RU_INDEP block at all | same |
| No firm-level exposure gradient in any war window | 31 firms, 85,065 firm-days; nominal only pre-war and in a full sample 59% pre-war; 0 of 10 survive BH | `outputs/tables/exposure_gradient_bh.csv` |

## Provisional — cite with the caveat attached

- **Ecosystem classification precision.** The hand-labelled audit was never run.
  What exists instead is an automated audit of the *register* against Wikidata
  (`scripts/run_register_audit.py`, thesis §4.6): **63 of 66 verifiable
  outlets agree, precision 0.955**, with 18 of 84 outlets
  unverifiable and counted neither way. Cite that figure rather than "the audit
  was not run", but cite it with its limit: it validates that each registered
  domain belongs to the country assigned, not that GDELT filed a given article
  under the right domain. Resolutions are pinned to a committed map; without the
  pin the figure is not reproducible, because Wikidata's name search is not
  stable.
- ~~**One committed table predates the `dw.com` fix.**~~ **Resolved, and the
  earlier version of this entry was wrong in a way worth recording.** It said the
  threat/act and held-out tables "*were* rebuilt with the corrected register".
  They were not. The rebuild ran, scanned 454 GB, and was discarded by a merge
  that kept the stale row on every collision, so the files came back
  byte-identical and looked rebuilt. Gate 3 reported pre-fix numbers throughout.
  All three tables are now genuinely rebuilt on the final register, verified by a
  differential check: only RU_INDEP and WEST move, by identical and opposite
  counts, and the Ukrainian and Russian-state series are byte-identical before
  and after — which is what confirms the state-vs-Ukraine contrast was never
  affected.

## Known-stale statements in otherwise-valid documents

| document | stale claim | correction |
|---|---|---|
| [`data_sources.md`](data_sources.md) §2–3 | the equity half cannot be built without a vendor key | true of cloud sessions only; built free from a residential IP — **banner added** |
| [`research_plan.md`](research_plan.md) §9 | odds table presented as live priors | every row now settled — **banner added** |
| [`gate1_gate2_results.md`](gate1_gate2_results.md) §8 | "1,605 days ingested, not 4,151" | correct for that gate; coverage is now 4,027 days |
| [`gate3_preregistration.md`](gate3_preregistration.md) §control | "Gate 2 passed this control (Western block at p=0.0005)" | it does not. On the corrected register the Western block survives correction nowhere in Gate 2 (smallest adjusted p 0.082). **The document is deliberately unedited** — a pre-registration that is revised after the fact is not a pre-registration, and this is the mechanism for recording that without touching it. Thesis §6.1 states the corrected position |
| [`gate4_preregistration.md`](gate4_preregistration.md) §exploratory | gas exploratory result at p=0.0005 | 0.0028 on the corrected register, and 0.399 on the pre-registered 222-day sample. Unedited for the same reason |

Gate documents describing the sample *they* were run on are correct as written
and are not stale. A gate result must report the data it used, not the data that
exists now — re-estimating a pre-registered test on later-arriving data is the
failure mode Gate 3 documents.

## Rule

Any new document that reports a result must either appear in the **Live** table
here or carry its own banner. A finding that is not in this file has not been
checked against the retractions.
