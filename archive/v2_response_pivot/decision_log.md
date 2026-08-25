# Decision Log — v2

Continues from `thesis_v1/decision_log.md`, which records all v1 decisions
and is preserved unchanged. Only new/v2-scoped decisions go here.

Format: same as v1 (Decision / Reason / Alternatives considered /
Consequences / Revisit condition).

---

## 2026-07-01 — Make-or-break identification tests run; centerpiece (H4) falsified

**Decision:** Before committing the full execution plan, ran the two cleanest
identification tests (advisor-mandated). Result: the intended novel
centerpiece — that defense-equity response scales with firm defense-revenue
exposure (H4) — is **falsified**. Consequently the plan's headline shifts from
"firm-level heterogeneous response by war exposure" to "the media-driven
**threat/expectations** channel (GPR_THREAT) + a robust null-map + efficiency
+ descriptive multilingual narrative."

**Reason:** Under two-way (firm + day) fixed effects, `intensity_spike ×
SIPRI-exposure` is null on volatility (p=0.82) and returns (p=0.76);
continuous exposure p=0.99; binary pure-play p=0.82; descriptively the vol
bump is *larger* for civil-heavy firms than defense pure-plays. Day FE absorbs
the market/VIX/macro confound, so this is the clean test — and it says defense
firms do **not** respond to conflict intensity in proportion to their defense
exposure. The surviving uniform vol bump (§6.3 of research_plan) does not
scale with exposure and is therefore likely a residual A&D-sector confound,
not a defense-war response. Separately, the fair symmetric channel test
(GPR_ACT vs GPR_THREAT, index level, market+VIX controls) shows European
defense volatility loads on **THREAT/expectations** (p<0.001) more than on
realized ACT (p=0.21) — a real, modest, and directionally counter-intuitive
positive that becomes the new headline candidate.

**Alternatives considered:** (a) Write the plan around firm-exposure
heterogeneity anyway. Rejected — the key test is already null; building on it
would waste months. (b) Abandon v2 entirely. Rejected — a defensible thesis
remains (threat channel + null-map + descriptive), just not a slam-dunk.

**Consequences:** `research_plan.md` rewritten to lead with the honest
evidence (§2), revise all hypotheses (§3, H4 marked FALSIFIED, H2 threat-
channel promoted), and include an explicit significance assessment (§11:
LOW odds for a clean firm-heterogeneity positive, MODERATE for the threat-
channel headline, HIGH for the comprehensive efficiency/null-map/descriptive
thesis). Compute confirmed light (no Colab needed for core). SIPRI matched
87/128 firms; GPR ACT/THREAT verified usable.

**Revisit condition:** If a fuller market-factor model (Fama-French / rolling
betas) or a Ukraine-specific expectations instrument materially changes the
§6.4 threat-channel result, revisit the headline. If the programme requires a
clean strong positive (which this question, like v1, is unlikely to deliver),
revisit whether to proceed at all — this is flagged for the researcher's
decision before Phase 1.

**Decision:** Abandon the index-level OOS forecasting question as the
thesis headline. Adopt: *"Do defence and defence-related stocks respond more
strongly to realized conflict intensity or to media-driven geopolitical
expectations?"*

**Reason:** An independent supervisor audit (`docs/v1/supervisor_audit.md`)
found that both the returns and volatility forecasting arms fail a properly
specified out-of-sample incremental test (Clark–West, standardized/
regularized, war-regime trend controlled) on the real WAERLST/BSHIELDT
indices, not just the ITA proxy. Follow-up firm-level testing in-session
showed a robust, significant **contemporaneous** response of firm-level
idiosyncratic volatility to realized attack intensity (p < 0.001, survives
date-clustering, VIX control, and common-factor removal) that is invisible
at the index level and absent for media attention. This is a genuine,
testable, novel result; the forecasting null becomes supporting evidence
(market efficiency) rather than the main finding.

**Alternatives considered:**
- (A) Keep the topic, write v1 up as a rigorous null. Rejected as primary
  path — thin contribution, though the null remains valid supporting
  evidence (§6 of the v2 plan).
- (C) Change topic entirely. Rejected — discards ~80% of working
  infrastructure (financial, attack, GDELT pipelines) for no clear gain; the
  firm-level pivot (B) already produces a positive result with the same data.

**Consequences:** New unit of analysis (firm panel, not index), new design
(contemporaneous response, not multi-day-ahead forecast), two new data
sources (GPR, SIPRI), narrative gap repositioned from predictor to
descriptive/controlled channel. v1's code/data/outputs are archived in
`thesis_v1/`, not deleted, and several v1 processed tables are reused
directly (see `docs/v1/README.md`).

**Revisit condition:** If the firm-panel response result (§3.2 of the v2
plan) fails to replicate under the formal Phase 3 specification (correct
clustering, common-factor and VIX controls, war-sample restriction), revisit
whether a response design is viable at all before falling back to option (A).

---

## 2026-07-01 — Project restructured into thesis_v1 / thesis_v2 / docs

**Decision:** Split the repository into `thesis_v1/` (all v1 code, data,
outputs, and root-level project files, archived), `thesis_v2/` (fresh
skeleton for the new design), and a shared `docs/` at the top level with
`docs/v1/` (historical, do-not-edit) and `docs/v2/` (active planning/status).

**Reason:** The pivot changes the unit of analysis, design, and some data
sources enough to warrant a clean codebase rather than patching the v1
pipeline in place — while explicitly preserving v1's outputs and data for
reuse and citing them as the empirical trigger for the pivot.

**Alternatives considered:** Patch v1 in place (branch or in-repo rewrite).
Rejected — v1's `docs/` audits and `decision_log.md` are a valuable, citable
record of what was tried and why it changed; overwriting them would lose
that trail. A clean `thesis_v2/` also avoids fighting v1's OOS-forecasting-
specific code structure (`ExpandingWindowEngine`, F/P/N/PN/PNG info sets)
that doesn't map cleanly onto a panel-response design.

**Consequences:** `thesis_v2/config`, `data`, `notebooks`, `outputs`,
`scripts`, `src`, `tests` start empty (skeleton with `.gitkeep`); config
templates (`gdelt_queries.yaml`, `source_groups.yaml`, `country_groups.yaml`,
`paths.yaml.example`, `requirements.txt`) copied from v1 as starting points
since the underlying attack/GDELT/financial pipelines are reused, not
rebuilt. `AGENTS.md` at the project root was rewritten to describe the new
layout for future agent sessions.

**Revisit condition:** None expected; this is a structural decision, not a
scientific one.

---

## 2026-07-01 — Reused v1 data, added GPR + SIPRI

**Decision:** Reuse v1's real Bloomberg WAERLST/BSHIELDT (index +
constituent-level), attack, and GDELT processed tables as-is for v2 (no
re-extraction). Add two new sources: GPR daily index (Caldara & Iacoviello)
and SIPRI Top-100 arms-revenue data, both recovered from
`thesis_v1/thesis_old_try/data/raw/{gpr,sipri}/` (an even earlier thesis
attempt) and verified this session to be correct, current-enough, and
directly usable without re-download.

**Reason:** v1's financial/attack/GDELT data collection was itself sound
(the null was a design problem, not a data problem) — see
`docs/v1/supervisor_audit.md`. GPR's `GPRD_ACT`/`GPRD_THREAT` split gives an
independent, language-agnostic operationalization of exactly the
intensity-vs-expectations contrast in the new research question. SIPRI's
arms-revenue-share is the standard defense-exposure measure needed for the
firm-heterogeneity hypothesis (H4).

**Alternatives considered:** Re-extract financial/attack/GDELT data fresh
for v2. Rejected — no evidence the v1 extraction was flawed; re-extracting
would cost significant time for no expected benefit. Download a fresh GPR
export instead of reusing the old-attempt file. Rejected — the existing
daily file already covers 1985–2026-06-15 at daily frequency with the exact
columns needed; no reason to re-fetch.

**Consequences:** GPR is monthly/global in its `_export` variant (not used)
and daily/global in the `_daily_recent` variant (used) — it is not
Ukraine-specific, so it validates the intensity-vs-expectations contrast
but does not replace the attack/GDELT data as the primary channels. SIPRI
requires manual company-name-to-ticker matching (~50 firms) and stops at
2024 (2025–26 not yet published; carry 2024 forward as the latest exposure
estimate).

**Revisit condition:** If SIPRI name-matching fails for a large share of
WAERLST/BSHIELDT constituents, consider a simpler binary
"defense-pure-play vs. diversified" classification from `bics_industry` /
`index_membership` in `firms_metadata_old.csv` instead of continuous
exposure.

---

## 2026-07-01 — Narrative gap repositioned; forecasting demoted, not removed

**Decision:** The narrative-gap feature is kept, but no longer as a
return-forecasting predictor (v1's H3, which failed). It now serves as (1)
a descriptive/novelty measurement of cross-ecosystem (UA/RU/Western) framing
divergence of the same events, and (2) one channel in the new response
horse race, where it is shown to be significant but small and dominated by
physical intensity. Separately, the index-level OOS forecasting result from
v1 is **kept** as a supporting "efficiency" chapter (the response is
contemporaneous, not exploitable ahead of time), not deleted.

**Reason:** Both changes were validated empirically in-session (see
`docs/v2/research_plan.md` §3.3 for the narrative-gap horse-race result, and
v1's `supervisor_audit.md` for the forecasting null). Removing forecasting
entirely would discard a real, already-established result (efficiency) that
directly supports the new headline claim.

**Alternatives considered:** Drop forecasting entirely to keep scope tight.
Rejected — it costs little (mostly fixing already-written v1 code) and adds
an efficiency argument that strengthens rather than dilutes the response
story. Make narrative gap a full standalone hypothesis again. Rejected —
the evidence shows it is dominated by intensity; treating it as a headline
hypothesis would overclaim.

**Consequences:** Phase 5 of the v2 plan explicitly scopes the forecasting
work to fixing v1's 48 failing tests and closing v1's open C7 (h=5) / C8
(GARCH-X) items, not re-designing the forecasting pipeline.

**Revisit condition:** None expected.
