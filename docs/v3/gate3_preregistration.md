# Gate 3 — pre-registration of the threat/act split test

**Written:** 2026-08-20, **before** the indices were built and before any
regression on equity returns was run. Nothing below was chosen after seeing an
outcome.

## Why this document exists

Gate 1 and Gate 2 were each renegotiated after seeing data. The basket test
failed on its stated criteria and was rescued by the "overriding criterion" in
`equity_validation.md` §3; the GPR external check failed in changes and was
re-specified to levels. **Both renegotiations were individually defensible and
both were, in fact, correct** — but a third would stop being credible. So the
grid, the mapping, and the decision rule are fixed here in advance.

## What is being tested

Gate 2 found that local-language ecosystems add nothing over Western ones for
defence-equity returns, using **attention share** and **mean tone**. Those are
crude: they measure how *much* an ecosystem covers the conflict and how negative
it is, not *what kind* of coverage it is.

The sharper question, and the one `research_plan_v3.md` §5.4 actually specifies,
is whether ecosystems differ in **anticipation versus realization** — does
Ukrainian media signal a coming escalation before Western media does? A media
ecosystem can carry the same volume and the same tone while being systematically
earlier. Attention and tone cannot see that; a threat/act split can.

**This is the last specification under which the asset-pricing headline can
survive.** If it fails, the Gate-2 null is final.

## The measurement, fixed now

GDELT's GKG themes are applied by the same classifier to machine-translated text
in all 65 source languages. That is a real advantage over the plan's §5.4
proposal of per-language Caldara–Iacoviello dictionaries: it removes
cross-language equivalence as a source of error entirely, rather than requiring
it to be validated by hand. The cost is that the taxonomy is GDELT's rather than
Caldara–Iacoviello's, so the mapping below is an interpretation, fixed in
advance and reported as such.

Following Caldara & Iacoviello's logic — THREAT is war/peace threats, military
build-ups, nuclear and terror threats; ACT is the beginning and escalation of
war and realized terror acts:

**ACT themes (realized violence):**
`KILL`, `WOUND`, `CRISISLEX_T03_DEAD`, `CRISISLEX_T02_INJURED`,
`ARMEDCONFLICT`, `TERROR`, `SIEGE`, `REBELLION`, `MANMADE_DISASTER_IMPLIED`

**THREAT themes (anticipation, capability, deterrence):**
`THREATEN`, `MILITARY`, `TAX_WEAPONS`, `TAX_FNCACT_TROOPS`, `BORDER`,
`NUCLEAR`, `SANCTIONS`, `EPU_CATS_NATIONAL_SECURITY`, `USPEC_UNCERTAINTY1`,
`SECURITY_SERVICES`

Per ecosystem *e* and day *t*, over conflict-tagged articles only:

- `act_share`    = ACT-tagged articles / conflict articles
- `threat_share` = THREAT-tagged articles / conflict articles
- `ta_ratio`     = threat_share / act_share  — the anticipation intensity

Shares of the ecosystem's own conflict output, never raw counts, for the reason
in §5.4: GDELT's source coverage drifts by a factor of 2.5 across the sample.

## The test grid, fixed now

- **Timing:** news lagged **one day**, primary. Established empirically in
  `gate1_gate2_results.md` §6b — GDELT days are full UTC days and European
  markets close ~16:30 UTC. Same-day reported as secondary only.
- **Frequencies:** daily and weekly (W-FRI).
- **Targets:** `r_bshieldt`, `r_waerlst` (Bloomberg, the referee), `r_ita`
  (validated proxy, clears four of five basket criteria), and `eu_defence`,
  `us_defence` (free baskets — reported, but the European one is weak at
  ρ=0.904 and carries no independent weight).
- **Windows:** Russia buildup+invasion (primary, theoretically motivated),
  all ingested days, 2017-19 episodes, 2025-26 episodes.
- **Specification:** return on the five ecosystems' `Δthreat_share` and
  `Δact_share`, plus regional market return and lagged VIX. HAC(5).
- **Statistic:** joint F-test of the three local ecosystems' threat *and* act
  terms (UA, RU_STATE, RU_INDEP), **conditional on** WEST and EN_GLOBAL.
- **Correction:** Benjamini–Hochberg at FDR 5% across the entire grid. No cell
  is reported as a finding on its nominal p-value.
- **Minimum 4 observations per parameter**, so thin windows are excluded rather
  than overfitted.

## The decision rule, fixed now

**PASS** requires *either*:

- at least one BH-surviving cell **in the Russia buildup+invasion window**, on a
  Bloomberg target or ITA; or
- BH-surviving cells in **at least two independent episode windows**, same sign.

**FAIL** is anything else — including the pattern Gate 2 produced, where
survivors appear in one thin window and vanish when a convention changes.

A single BH survivor in a non-Russia window, or one that appears under only one
timing convention, is **not** a pass. That is the exact failure mode already
observed once, and it will not be reinterpreted as success.

## Positive control

The same regression must detect the **Western** threat/act block somewhere. If
neither block is detected anywhere, the result is uninformative about local
media — it means the design lacks power — and must be reported as such rather
than as a null. Gate 2 passed this control (Western block at p=0.0005).

## What a pass would mean

That defence equities respond to *anticipation as measured by local media*
beyond what Western coverage conveys — i.e. local media are earlier, and the
market reads them. That is the Bondarenko et al. result transplanted to asset
prices, and it would carry the thesis.

## What a fail would mean

The Gate-2 null becomes final and the thesis's headline is the null: Western
defence equities price the Western narrative, and local perception — in volume,
in tone, and in anticipation structure — adds nothing. The contribution then
rests on the measurement chapter, the censorship wedge, and the market-control
retraction, which is a defensible thesis but not a positive one.
