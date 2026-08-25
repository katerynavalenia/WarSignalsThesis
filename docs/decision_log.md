# Decision Log — v3

Continues from the archived iterations in [`../archive/`](../archive/), which are
both preserved unchanged. Only new v3-scoped decisions go here.

Format: Decision / Reason / Alternatives considered / Consequences /
Revisit condition.

---

## 2026-08-17 — v1 news indicators found invalid; sample extended to 2015; topic kept

**Decision:** Keep the research topic and every existing pipeline. Rebuild the
GDELT indicators from the **GDELT 2.0 Translingual** archive over
**2015-02-18 → 2026-06-30**, classifying articles by *publisher* (country,
language, state-controlled vs independent) rather than by the country the
article mentions. Demote the air-attack dataset from sample-defining constraint
to a short-sample refinement. Reframe the question as **"whose perception of
geopolitical risk is priced in defence equities?"**

**Reason:** Answering supervisor comment #3 (describe the sentiment methodology)
uncovered that `thesis_v1/gkg_bulk_download.py` downloads the **GKG 1.0 daily
stream**, which is effectively English-only — measured, 2025-03-01: 7 `.ru` and
21 `.ua` articles out of 60,690 — and that 88.6% of articles were assigned a
national group by the most-mentioned country in the `LOCATIONS` field. The three
"national sentiment" series are therefore topic proxies drawn from one media
population, which explains both their mutual collinearity and the flat horse
race across information sets. Separately, the Sep-2022 start was a hardcoded
`START = date(2022, 9, 29)` matching the attack data, not a GDELT constraint;
the translingual archive (390,440 files, 4.19 TB) runs from 2015-02-18. Fixing
the measurement and extending the sample are the same action, and together they
answer supervisor comments #1 and #3. Bondarenko, Lewis, Rottner & Schüler
(2024, *JIE* 152:104005), which the supervisor asked us to cite, find that
local-language geopolitical-risk shocks move the Russian economy while
English-language ones do not — our v1 indicators sat entirely on the
English-language side of exactly that comparison.

**Alternatives considered:** (a) Keep v1's indicators and only extend the
sample. Rejected — a longer series of an invalid measure is still invalid, and
the methodology section could not be written honestly. (b) Continue with v2's
contemporaneous-response pivot. Rejected as the headline — its centrepiece (H4)
was already falsified, though its surviving evidence is folded into v3.
(c) Change topic. Rejected — nothing about the question was wrong; the sample,
the measurement, and the evaluation metrics were.

**Consequences:** n rises from ~920 to ~2,850 trading days and the February-2022
re-rating moves inside the sample. Requires a new GDELT ingestion (BigQuery
preferred; bulk download as fallback) and a curated outlet register with a
hand-labelled precision audit. Bloomberg index files start 2020, so the long
sample needs either a re-pull or a free long-history defence basket validated on
the overlap. Forecast evaluation moves to Campbell–Thompson R²_OS with
Diebold–Mariano, Clark–West, MCS and multiple-testing control (supervisor
comment #4); the numerically degenerate GARCH-X-in-mean is replaced by HAR-RV-X.

**Revisit condition:** The Phase-2 gate. If the rebuilt indices fail their
validation battery — no hand-labelled precision, no correlation with published
GPR, no event face validity, or still mutually collinear — stop before Blocks
B–E and reconsider.

---

## 2026-08-25 — The classification rule for outlets that publish across borders

**Decision:** State-funded external broadcasters classify to the state that funds
them, whatever language they publish in and whatever audience they address.
Exile newsrooms classify to their country of origin, not their country of legal
domicile. This moves `svoboda.org` and `currenttime.tv` (Radio Free Europe /
Radio Liberty) from `RU_INDEPENDENT` to `WEST_REGISTER`, joining `dw.com`, and
it keeps `meduza.io`, `novayagazeta.eu`, `tvrain.ru` and `moscowtimes.ru` in
`RU_INDEPENDENT`. **Register changes stop here.** Everything else the audit
flagged is adjudicated in text rather than acted on.

**Reason:** The register previously had no stated rule for outlets whose
publisher, language and audience point to different countries, and without one
the `dw.com` fix looked like a one-off correction rather than an application of a
principle. It was not: RFE/RL is the same case — a government-funded foreign
broadcaster with a Russian-language service — and it sat unfixed in the same set.
The automated Wikidata audit (`scripts/run_register_audit.py`) flagged
`svoboda.org` independently, with country of origin Q30, United States;
`currenttime.tv` is the same organisation and follows by rule rather than by
evidence, which is recorded rather than glossed.

The rule has to cut both ways or it is not a rule. Applied to exile newsrooms it
gives the opposite answer: Meduza is a Russian newsroom reporting for a Russian
audience from Riga, and Wikidata's country of origin for it (Q211, Latvia)
records where it is registered, not whose perception it carries. The audit's
Meduza flag is therefore dismissed on the record.

**Alternatives considered:** (a) Move nothing and note the audit's flags as
limitations. Rejected — shipping a thesis whose own audit table prints an
unfixed instance of an error class the thesis devotes a section to is
indefensible. (b) Follow Wikidata mechanically wherever it disagrees. Rejected —
it would move the exile newsrooms out of the Russian ecosystem, which measures
legal domicile rather than editorial perspective and would empty the independent
Russian block of the outlets that define it. (c) Drop the cross-border outlets
from every ecosystem. Rejected — it discards real coverage and the aggregator
exclusion already covers the case where there is no editorial voice to place.

`strana.news` is a third flag and a false positive: the Wikidata search resolved
to Q2642423, an entity named "Strana" with country Q224 (Croatia), not
Strana.ua. It is documented and kept.

**Consequences:** Every GDELT-derived table has to be re-ingested, because
`build_case_sql` compiles the register into the query — the ecosystem tables, the
Gate-5 holdout, and the threat/act tables, about 1.9 TB of BigQuery scan. Only
`RU_INDEP` and `WEST` volumes change; the Ukrainian and Russian-state series,
which carry the thesis's live tone finding, are untouched by construction. The
independent Russian block loses volume for the second time, which further weakens
the state-versus-independent contrast already retracted in `findings_status.md`
as underpowered.

**Revisit condition:** A future ingest that adds outlets to the register must
apply the rule above at the point of adding, and re-run the audit. If the audit's
verifiable coverage rises materially above the current 40 of 84 outlets and
turns up mismatches in `RU_STATE` or `WEST` — the blocks carrying live claims,
both currently at 1.000 precision — the affected result must be re-derived before
it is reported.

---

## 2026-08-25 — Recover SQ5 from public sources rather than record it as untestable

**Decision:** Rebuild firm-level war exposure from SIPRI's published Top-100
arms-revenue tables and test the exposure gradient across the February-2022
break, rather than reporting the question as untestable because the project's
copy of the firm panel was lost.

**Reason:** The thesis had inferred from *our copy is gone* to *this cannot be
tested*. That inference does not hold for a measure built from an annually
published public dataset. SIPRI reports arms revenue and total revenue per firm;
their ratio is the standard continuous exposure measure, and prices for the
listed producers come from the endpoint the equity spine already uses. What is
genuinely unrecoverable is the *index constituent panel* — no public source gives
Bloomberg's daily WAERLST membership and weights — and that distinction is now
drawn in §3.7 rather than collapsed.

**Alternatives considered:** (a) Fuzzy-match SIPRI names to tickers with
`rapidfuzz`. Rejected — "General Dynamics" and "General Electric" are close in
string distance and nothing alike in exposure, and a mismatch would attach the
wrong exposure to the wrong returns without failing any test. The map is
hand-curated for that reason. (b) Use a time-varying annual arms share. Rejected
— it would make the gradient partly a story about firms changing business mix;
the sample mean is the stable summary the question needs. (c) Leave it as future
work. Rejected — it was a day's work and it closes a supervisor-visible gap.

**Consequences:** 31 listed firms, 85,065 firm-days, arms shares 0.033–0.943, the
re-rating inside the sample. Result: no gradient in any war window, two nominal
hits (pre-war and a full sample dominated by it), nothing surviving
Benjamini–Hochberg. Reported in §8.7. §3.7 and §9.4 are corrected accordingly.

**Revisit condition:** If index constituent panels are ever recovered, the
gradient should be re-estimated on the actual index members rather than on the
SIPRI intersection, which over-represents large listed producers.
