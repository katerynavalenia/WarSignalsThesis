# Gate 5 — result: FAIL. Five for five, and that is the finding.

**Date:** 2026-08-23 · **Pre-registration:** [`gate5_preregistration.md`](gate5_preregistration.md)
**Code:** `thesis_v2/scripts/run_gate5_escalation.py`
**Data:** 651 usable days from 954 ingested *after* the hypothesis was written

## Verdict

| condition | result |
|---|---|
| 1. GPR_ACT survives BH at both horizons | **FAIL** — p=0.159 (h=1), p=0.301 (h=5) |
| 2. shuffle placebo p > 0.20 | PASS — 0.557, 0.799 |
| 3. survives twelve own-dynamics lags | **FAIL** — 0.143, 0.566 |

The design was clean — the placebo confirms it, and the Western block is still
detected in two cells (GPR_THREAT h=1 at p=0.006; GPR_ACT h=5 at p=0.041), so
there is power. The effect simply is not there.

## What did not replicate

The exploratory evidence was, by the standards of this project, unusually good.
The local block predicted changes in realized geopolitical acts in **both halves
of the in-sample period independently** — p=0.039 and 0.024 in 2017–2021, p=0.0001
and 0.0000 in 2022–2026 — survived twelve lags of own dynamics, and passed a
time-shuffle placebo. In the earlier half the Western block was null while the
local block was not, which is precisely the asymmetry Bondarenko et al. (2024)
report.

On 651 days the hypothesis had never seen, it is p=0.16.

**Split-half replication inside a sample is not out-of-sample replication.** Both
halves shared the same eleven-year construction, the same outlet register, the
same GDELT coverage regime and the same persistent-levels specification. Whatever
produced significance in one half produced it in the other for the same reason,
and neither carried to fresh data.

## Five for five

| # | claim | how it looked | what killed it |
|---|---|---|---|
| 1 | GPR_THREAT raises European defence volatility | p<0.001 | correct regional market control |
| 2 | Threat shocks move defence returns in the build-up | p=0.0001 | the same — SPX → SXXP |
| 3 | Local media's threat/act structure is priced | 7 BH survivors | adding the held-out window |
| 4 | Local perception is priced in European gas | p=0.0005, clean placebos | pre-registered replication, n 81 → 222 |
| 5 | Local media anticipate realized escalation | both halves significant | pre-registered held-out sample |

Each was significant at conventional levels. Each had a plausible mechanism.
Each survived at least one robustness check. **None survived the check designed
to kill it.**

The five failure modes are all different: two omitted-variable problems, one
truncated sample, one small sample, and one in-sample-split that did not
generalise. That is not one mistake repeated; it is five distinct ways for a
media-and-markets study to produce a convincing artefact.

## Why this is the thesis

The conclusion is unchanged and now very hard to dislodge:

> Local-language perception of the Russia–Ukraine conflict is not priced in
> Western defence equities or in European natural gas, and does not anticipate
> realized escalation once tested out of sample. Western coverage is what
> markets track, and the apparent contributions of local media do not survive
> correct controls, adequate samples, or held-out data.

The methodological contribution is the stronger half. Five pre-registered or
control-based tests, five retractions, with the sequence documented rather than
buried, is a more useful result for anyone doing this kind of work than a sixth
attempt would have been.

## Stop

No sixth test. The question has been asked of two asset classes and one
non-market outcome, with pre-registered protocols, passing positive controls, and
clean placebos. The remaining uncertainty is not resolvable by trying again on
the same data — every held-out window in this dataset has now been used.

What is left is to write it.
