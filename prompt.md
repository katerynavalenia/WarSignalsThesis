You are initializing the codebase for a Master 2 thesis project titled:

**War Signals and Defense Equity Risk: Physical Air-Attack Intensity versus Multilingual News Narratives**

The project tests whether unexpected Russian air-attack intensity, weapon composition, interception outcomes, and multilingual news narratives improve out-of-sample forecasts of defense-equity returns and volatility.

## Existing project context

The repository already contains:

* `Master_Thesis_Research_Completion_Plan.md`
* `Initial-research-specification.txt`
* `Brainstorm-session-1-summary.txt`

Read all three files before making changes.

Treat `Master_Thesis_Research_Completion_Plan.md` as the authoritative and complete research execution plan. Keep it in the repository as the main plan context for all future agents.

Do not replace, shorten, rename, or duplicate it.

`Initial-research-specification.txt` provides supporting methodology.

`Brainstorm-session-1-summary.txt` contains earlier ideas only and must not override the completion plan.

## Task

Inspect the existing repository and initialize a clean, maintainable research codebase.

### 1. Create one root context file: `instructions.md`

This must be the only AI-agent instruction file. Do not create `AGENTS.md` or nested instruction files.

Keep it concise. It should tell future agents to:

* read `Master_Thesis_Research_Completion_Plan.md` first;
* use it as the full research plan and source of truth;
* read `instructions.md` for operational coding and repository rules;
* treat the research as predictive, not causal;
* preserve raw data unchanged;
* avoid look-ahead bias and random train/test splits;
* use time-series validation and training-only preprocessing;
* compare models on identical forecast dates;
* use point-in-time constituents for historical firm analysis;
* keep the index-level study as the core;
* treat firm-level, intraday, procurement, sanctions, and deep-learning work as optional;
* document assumptions, outputs, validation, decisions, and unresolved issues after every task.

Do not copy the full research plan into `instructions.md`. Reference it instead and summarize only durable operational rules.

### 2. Create the basic repository structure

Create missing directories without destructively reorganizing existing work:

```text
config/
data/raw/
data/interim/
data/processed/
data/external/
docs/
notebooks/
src/data/
src/features/
src/models/
src/utils/
tests/
outputs/figures/
outputs/tables/
outputs/model_objects/
outputs/logs/
thesis/
```

Add minimal `__init__.py` and `.gitkeep` files where appropriate.

Do not create empty speculative modules for the full future pipeline.

### 3. Create or update

* `README.md`
* `instructions.md`
* `decision_log.md`
* `docs/project_status.md`
* `docs/data_dictionary.md`
* `docs/source_inventory.md`
* `.gitignore`
* a minimal dependency file
* minimal non-secret configuration templates

The `README.md` and `instructions.md` must link clearly to `Master_Thesis_Research_Completion_Plan.md`.

Mark unaudited data, fields, and sources as planned or unverified. Do not invent Bloomberg fields, confirmed coverage, credentials, sources, or results.

## Important research context

* Primary outcome: `WAERLST`.
* Main robustness outcome: one European aerospace-and-defense index, still to be selected after the data audit.
* Additional robustness outcome: `BSHIELDT`.
* Main frequency: daily.
* Main design: strict out-of-sample forecasting.
* Conservative timing: information available through day `t` predicts the market outcome on trading day `t+1`.
* Core study: index level.
* Immediate next phase: Bloomberg financial-data audit.

Volatility approach must depend on audited data availability:

1. genuine intraday data → realized volatility;
2. daily OHLC → range-based volatility;
3. close-only data → absolute or squared returns and GARCH.

HAR-RV must remain optional and must not block the thesis.

## Do not yet

* download external data;
* query GDELT;
* scrape attack reports;
* calculate returns;
* select the European index without evidence;
* build forecasting models;
* add heavy ML or NLP dependencies;
* generate synthetic research results;
* commit or push changes.

## Validation

After setup:

* verify Markdown links;
* verify configuration syntax;
* verify Python package imports;
* verify that `.gitignore` preserves source code and documentation;
* check consistency between `instructions.md`, `README.md`, the decision log, project status, and `Master_Thesis_Research_Completion_Plan.md`;
* run existing tests if available.

## Final response

Report:

1. repository state before changes;
2. files created or modified;
3. architectural decisions;
4. validation performed;
5. unresolved issues;
6. recommended next action.

The recommended next action should be:

**Audit the Bloomberg delivery and determine the available fields, date coverage, series type, index identifiers, and feasible volatility target.**
