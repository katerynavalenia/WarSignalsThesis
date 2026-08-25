# Whose Perception of Geopolitical Risk Is Priced in Defence Equities?

**Evidence from the Russia–Ukraine War** · Master-2 thesis, empirical finance

**This repository is the final state of the research.** Everything in it belongs
to one study. Earlier iterations are in [`archive/`](archive/) and are kept only
because the thesis cites them.

---

## The finding

Western defence equities price the **Western** narrative. Local-language
perception — Ukrainian media, Russian state media, Russian independent media —
adds nothing beyond it, in coverage volume, in tone, or in the
anticipation-versus-realization structure of that coverage.

The null holds across two asset classes and one non-market outcome, each against
a positive control confirming the design detects Western media where Western
media matter:

| tested | result |
|---|---|
| Defence equities (Gates 2, 3) | not priced |
| European natural gas (Gate 4) | not priced |
| Realized escalation (Gate 5) | does not anticipate, out of sample |
| Out-of-sample return predictability | none — R²_OS of 1.0% detectable at 80% power, best observed 0.45% |

Two further results survive. **Russian state media's tone did not move when
Russia invaded Ukraine** — +0.02, and −0.05 on a fixed panel of twenty-four
outlets present on both sides — while Ukrainian media's fell 1.66 points. And
**five apparently significant findings were produced and retracted** over the
course of the work, by five distinct mechanisms. That sequence is reported rather
than removed, and is the methodological contribution.

## Read in this order

1. **[`thesis/README.md`](thesis/README.md)** — chapter index, and a table
   mapping each of the supervisor's five review comments to the section that
   answers it.
2. **[`thesis/01_introduction.md`](thesis/01_introduction.md)** through
   `09_conclusion.md` — the thesis, 17,165 words.
3. **[`docs/findings_status.md`](docs/findings_status.md)** — **read this before
   citing any number.** Six claims in `docs/` were retracted, and the documents
   that reported them are kept unedited because the retraction sequence is part
   of the thesis. This page is the authority on which results are live.
4. **[`docs/reproduce.md`](docs/reproduce.md)** — how to rebuild everything.

## Layout

```
thesis/       the write-up: 9 chapters, references.bib, build.sh
docs/         research documentation — pre-registrations, gate results, diagnosis
src/          library code: data loaders, feature construction, estimators
scripts/      the pipeline, from BigQuery ingest to figures
tests/        85 tests, all offline
data/         interim tables (5 tracked parquets); raw data is gitignored
outputs/      40 result tables, 2 figures
archive/      superseded iterations, kept because the thesis cites them
```

## Rebuilding

```bash
bash bootstrap.sh && source .venv/bin/activate
python -m pytest tests/ -q          # 85 tests, no network, no credentials

python scripts/ingest_gdelt.py --preset full        # needs BigQuery
python scripts/run_gates.py                          # Gate 1 + Gate 2
python scripts/run_forecast_null.py                  # OOS grid + power curve
```

Full run order, costs and outputs: [`docs/reproduce.md`](docs/reproduce.md).

Two things cannot be rebuilt from this repository alone, and the thesis says so
rather than hiding it: the **Bloomberg index series** (proprietary, gitignored,
mirrored to Drive) and the **firm-level constituent panel**, which no longer
exists anywhere — which is why there is no cross-sectional chapter.

## The pre-registrations

Gates 3, 4 and 5 were written down *before* the data to test them existed. Each
pre-registration is committed separately and earlier than its result, so the
order is verifiable in the history rather than asserted:

| gate | question | verdict |
|---|---|---|
| [3](docs/gate3_preregistration.md) | is the threat/act structure of local media priced? | [FAIL](docs/gate3_results.md) |
| [4](docs/gate4_preregistration.md) | is local perception priced in European gas? | [FAIL](docs/gate4_results.md) |
| [5](docs/gate5_preregistration.md) | does local media anticipate escalation? | [FAIL](docs/gate5_results.md) |

## What is in `archive/`

- `v1_reviewed_draft/` — the audits and outputs of the version the supervisor
  reviewed. Chapter 4 cites its per-group precision figures; Chapter 3 cites its
  reconstructed-index statistics.
- `v2_response_pivot/` — the contemporaneous-response iteration. Chapter 8
  retracts its §6.4 result, so the source has to remain readable.
- `cloud_sessions.md` — setup notes for the previous directory layout.

Superseded *code* was deleted; git history has it. Superseded *documents* were
kept, because a thesis whose contribution is a retraction record cannot delete
the things it retracts.
