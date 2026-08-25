# CLAUDE.md

Guidance for Claude Code (claude.ai/code) working in this repository.

## What this is

The completed Master-2 thesis *Whose Perception of Geopolitical Risk Is Priced in
Defence Equities? Evidence from the Russia–Ukraine War* — write-up, pipeline,
data and documentation. **One version.** Earlier iterations were consolidated
away; what remains in `archive/` is there because the thesis cites it.

Start at [`README.md`](README.md), then [`thesis/README.md`](thesis/README.md).

## The rule that matters most

**Read [`docs/findings_status.md`](docs/findings_status.md) before citing any
number.** Six claims in `docs/` have been **retracted**, and the documents that
reported them are kept *unedited* because the retraction sequence is the thesis's
methodological contribution. Several files therefore state, in their own voice,
results that no longer hold.

Never cite as live: the GPR_THREAT defence-volatility result; the build-up threat
effect; the Gate-3 "pass"; the gas result; the escalation result; the
state-versus-*independent* censorship wedge. The state-versus-*Ukraine* tone
contrast is live and is the one the thesis claims.

## Layout

```
thesis/    9 chapters + references.bib, metadata.yaml, build.sh
docs/      pre-registrations, gate results, measurement diagnosis, reproduce.md
src/       data/ features/ models/ — loaders, index construction, estimators
scripts/   the pipeline: ingest -> gates -> figures
tests/     130 tests, all offline
data/      interim/ holds 7 tracked parquets; raw/ is gitignored
outputs/   tables/ (53 CSVs) and figures/ (2 PNGs)
archive/   superseded iterations, kept because the thesis cites them
```

Scripts run **from the repository root** (`python scripts/run_gates.py`), and
resolve `src/` via `sys.path.insert(0, parents[1])`.

## Commands

```bash
bash bootstrap.sh && source .venv/bin/activate
python -m pytest tests/ -q        # 130 pass, no network, no credentials
```

Full run order, BigQuery costs and per-script outputs:
[`docs/reproduce.md`](docs/reproduce.md).

## Conventions that are load-bearing

- **`date` is a regular column**, `datetime64[ns]`, never the index, in every
  persisted table.
- **Shares, never raw counts**, for anything derived from GDELT. Source coverage
  drifts by a factor of two-and-a-half across the sample; a count series would
  show that drift as a trend in every ecosystem at once.
- **Country dominates language** in ecosystem assignment. Ukrainian outlets
  publish heavily in Russian, so a language-first rule would file them as Russian
  media and manufacture agreement between the two ecosystems. The classification
  sensitivity analysis measures the cost of getting this wrong: under a
  language-first rule the Russian-independent block cannot exist at all, because
  the language tier claims those articles before the register is consulted.
- **State-funded external broadcasters classify to the funding state; exile
  newsrooms to their country of origin.** This is what puts Deutsche Welle and
  RFE/RL in the Western block and keeps Meduza in the Russian independent one.
  Both halves matter — a rule that only ever pointed one way would not be a rule.
  Three outlets were misfiled under it before it was written down.
- **Changes, not levels**, for regressors. Levels are persistent and produce
  significance that first-differencing removes — this killed one published claim
  already (`docs/gate1_gate2_results.md` §1).
- **Clark–West for nested comparisons, Diebold–Mariano only for non-nested.** DM
  is not valid under nesting; `src/models/evaluation.py` keeps them as separate
  functions so the distinction cannot be flagged away.
- **Parsing is split from fetching** everywhere, so tests never touch the network.

## Re-ingesting actually re-ingests — but check

`ingest_gdelt.py` merges fresh rows over existing ones with ``keep="last"``. It
used to keep the *first* row, and since existing data is concatenated first,
every re-query was silently resolved in favour of the stale copy — a 454 GB scan
ran, was billed, and was discarded, leaving Gate 3 on a superseded register for
weeks. After any re-ingest, confirm the file actually changed (`git diff --stat`)
and that only the ecosystems you expected moved.

## Before adding an expensive interim artefact

Put it on the `.gitignore` exception list **before** creating it. Two parquets
worth ~540 GB of BigQuery were destroyed by a worktree removal because they were
added to `data/interim/` but not to that list, and git treated them as scratch.

## Pre-registration

Gates 3, 4 and 5 were written down before the data to test them existed, and each
pre-registration is committed earlier than its result so the order is verifiable
in history. If a new test is run, follow that pattern: fix the grid, the
controls, the correction and the pass rule in a committed document first.

Both renegotiations that happened before this discipline was adopted were
defensible and are recorded; a third would not have been credible.

## Data that cannot be rebuilt here

- **Bloomberg WAERLST/BSHIELDT** — proprietary, gitignored, mirrored to
  `gdrive:WarSignalsThesis_Data/data/raw/bloomberg/`. Everything degrades to the
  free equity spine without them, losing only the referee comparison.
- **Firm-level constituents and SIPRI exposure** — gone entirely. This is why
  there is no cross-sectional chapter, and the thesis says so.
