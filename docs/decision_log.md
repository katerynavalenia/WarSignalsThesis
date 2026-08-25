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
