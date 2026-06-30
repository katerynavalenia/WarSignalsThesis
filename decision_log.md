# Decision Log

This file records all important methodological decisions for the thesis project.
Any AI agent or researcher must append new decisions here using the template below.

**Template** (from Section 19 of the research plan):

```markdown
## YYYY-MM-DD — Decision title

**Decision:**  
State what was chosen.

**Reason:**  
Explain the empirical or practical reason.

**Alternatives considered:**  
List credible alternatives.

**Consequences:**  
State what changes in data, models, or interpretation.

**Revisit condition:**  
State what new evidence would justify reopening the decision.
```

---

## 2026-06-28 — Delegate GPU and heavy-compute tasks to Google Colab

**Decision:**  
Use Google Colab (Pro subscription) for GPU-intensive and high-RAM tasks: GDELT article-level extraction (Phase 3), near-duplicate deduplication (Phase 3), multilingual transformer inference (Phase 4), and optional GARCH refitting / hyperparameter search (Phases 6–7). Google Drive serves as the shared storage bridge between Colab and local.

**Reason:**  
Phase 3 requires hundreds of GDELT API calls (hours of wall-clock time) and MinHash/LSH deduplication on 500K–2M articles (high RAM). Phase 4 requires scoring 500K–2M articles with a multilingual transformer (GPU needed — hours on CPU, minutes on T4). These tasks exceed typical laptop resources. Colab Pro provides T4/A100 GPUs, 32 GB RAM, and stable network.

**Alternatives considered:**  
- Run everything locally (rejected: transformer inference on CPU would take days; deduplication may OOM).
- Use a dedicated cloud VM (rejected: Colab Pro is simpler and already available).
- Use Kaggle GPUs (rejected: Colab Pro has better GDrive integration and longer sessions).

**Consequences:**  
- Colab notebooks with `colab_` prefix are stored in `notebooks/`.
- Colab-specific dependencies (transformers, torch, datasketch) are separated in `requirements.txt`.
- Intermediate outputs are saved to Google Drive as Parquet, then downloaded to local `data/interim/`.
- Phases 1, 2, 5, and 8 run locally only.
- All Colab runs must record runtime type, Python version, and package versions for reproducibility.

**Revisit condition:**  
If a local GPU becomes available or if Colab session limits become prohibitive.

---

## 2026-06-30 — Phase 4 two-tier approach: GDELT tone now, transformer after milestone

**Decision:**  
Split Phase 4 into two tiers. Tier 1 uses GDELT tone fields (already available from Phase 3) as the core multilingual sentiment/threat measure — no further work needed. Tier 2 (transformer enhancement) is deferred until after the first analytical milestone (§25: after Phase 6 produces the common out-of-sample forecast table). Manual article labeling (500+ articles across Ukrainian/Russian/English) starts now in parallel.

**Reason:**  
The GKG bulk data has no article text — only metadata and pre-computed tone fields. Transformer scoring requires fetching titles via DOC API (separate sample) and is not on the critical path. GDELT tone fields satisfy the minimum viable thesis requirement (§4.2). Per §25, transformer features should only be added after the first milestone. Per §18 priority order, NLP features are priority #8 — after baselines (#6) and ablation forecasts (#7).

**Alternatives considered:**  
- Zero-shot classification on all 11.4M GKG articles (rejected: no text available; zero-shot with English labels on non-English text is methodologically weak).
- Re-extract all articles via DOC API with titles (rejected: ~9 hours API time; creates inconsistent parallel dataset; not on critical path).
- Skip transformer entirely (rejected: §8.6 requires transformer evaluation; Tier 2 will address this after milestone).

**Consequences:**  
- Phase 5 and Phase 6 proceed using GDELT tone fields as the NLP measure.
- First milestone is reached without transformer features.
- After milestone: fine-tune `xlm-roberta-base` on labeled sample → score ~67K articles → re-run forecasts with enhanced N features.
- Manual labeling starts now (parallel human work, ~1–2 days).

**Revisit condition:**  
If GDELT tone fields prove insufficient for the thesis committee, escalate Tier 2 priority.

---

## 2026-06-28 — WAERLST as main financial outcome

**Decision:**  
Use Bloomberg `WAERLST` (global aerospace & defense index) as the primary financial outcome.

**Reason:**  
`WAERLST` provides broad global coverage of aerospace and defense firms and is available via Bloomberg. It is the most directly relevant equity index for studying defense-sector risk pricing.

**Alternatives considered:**  
- A single firm-level portfolio (rejected: index-level is the core study).
- A European-only defense index as primary (rejected: reserved for robustness).
- `BSHIELDT` as primary (rejected: reserved as additional robustness check).

**Consequences:**  
All primary return and volatility forecasts use `WAERLST`. Robustness uses a European index and `BSHIELDT`.

**Revisit condition:**  
If `WAERLST` is found to have severe data quality issues or insufficient history after the Bloomberg audit.

---

## 2026-06-28 — Daily frequency as main frequency

**Decision:**  
Use daily frequency as the main modeling frequency.

**Reason:**  
Attack data and news data are available at daily resolution. Daily financial data are confirmed from Bloomberg. Intraday data are not assumed to be available.

**Alternatives considered:**  
- Weekly frequency (rejected: loses too much daily variation in attacks and news).
- Intraday frequency (rejected: not confirmed to be available; reserved as optional extension).

**Consequences:**  
All core models, features, and evaluation operate at daily frequency. Intraday and HAR-RV are optional extensions.

**Revisit condition:**  
If genuine intraday data become available and the core thesis is already complete.

---

## 2026-06-28 — Predictive rather than causal framing

**Decision:**  
Frame the study as a predictive forecasting study, not a causal identification study.

**Reason:**  
The research question is about incremental out-of-sample predictive information, not causal effects. A credible causal identification strategy is not available given the data and design.

**Alternatives considered:**  
- Causal framing with event-study design (rejected: event studies are not the main method).
- Causal framing with instrumental variables (rejected: no credible instruments).

**Consequences:**  
Use predictive language only. Avoid "causes", "leads to", "has a causal effect on" unless a separate identification strategy is developed.

**Revisit condition:**  
If a credible causal identification strategy is developed and documented.

---

## 2026-06-28 — HAR-RV is optional

**Decision:**  
Treat HAR-RV (Heterogeneous Autoregressive Realized Volatility) as an optional extension, not a requirement.

**Reason:**  
Long historical intraday data are not assumed to be available. HAR-RV requires realized volatility from intraday bars. The thesis must be defensible without it.

**Alternatives considered:**  
- Require HAR-RV (rejected: would block thesis if intraday data unavailable).
- Use HAR-RV as the main volatility model (rejected: same reason).

**Consequences:**  
Volatility target follows a hierarchy: intraday → realized volatility; OHLC → range-based; close-only → absolute/squared returns + GARCH. HAR-RV is only pursued if intraday data exist and the core thesis is complete.

**Revisit condition:**  
If genuine intraday data are confirmed available during the Bloomberg audit.

---

## 2026-06-28 — One principal gradient-boosting model

**Decision:**  
Use one principal gradient-boosting algorithm (LightGBM or XGBoost), not both as equal main models.

**Reason:**  
The daily sample is relatively small. Using multiple algorithms as equal main models increases complexity and the risk of false positives from multiple comparisons.

**Alternatives considered:**  
- Both LightGBM and XGBoost as equal main models (rejected: unnecessary complexity).
- Random forest as main model (rejected: gradient boosting generally better for tabular data).
- Deep learning as main model (rejected: reserved as optional extension).

**Consequences:**  
Select either LightGBM or XGBoost after initial benchmarking. The other may be used for robustness only.

**Revisit condition:**  
If both algorithms give materially different results and a reviewer requests both.

---

## 2026-06-28 — Source groups based on geography and language

**Decision:**  
Classify GDELT news sources into Ukrainian, Russian, and Western information environments using both source geography and original language.

**Reason:**  
Language alone does not determine political viewpoint. A Russian-language Ukrainian source should not be automatically placed in the Russian information environment.

**Alternatives considered:**  
- Language-only classification (rejected: conflates language with viewpoint).
- Geography-only classification (rejected: misses important language-based framing differences).

**Consequences:**  
Source classification uses both dimensions. A Russian-language Ukrainian source is classified by geography first, with language as a secondary attribute.

**Revisit condition:**  
If a more nuanced classification scheme is needed and validated.

---

## 2026-06-28 — Index-level core; firm-level extension

**Decision:**  
Keep the index-level study as the core. Treat firm-level constituent analysis as an optional extension.

**Reason:**  
Firm-level analysis requires point-in-time constituents, membership dates, weights, and defense-revenue data — all of which introduce survivorship and look-ahead bias risks. The index-level study is feasible and defensible on its own.

**Alternatives considered:**  
- Firm-level as core (rejected: too many data requirements and bias risks).
- Both as equal pillars (rejected: firm-level should not block the core).

**Consequences:**  
Firm-level work begins only after the index-level thesis is complete and requires point-in-time constituents.

**Revisit condition:**  
If point-in-time constituent data are readily available and the core thesis is complete.

---

## 2026-06-28 — No event study as main design

**Decision:**  
Do not use event studies as the main research design. Use out-of-sample forecasting.

**Reason:**  
Event studies focus on a small number of event dates and cannot test incremental predictive information continuously. The thesis contribution relies on daily signals and strict out-of-sample evaluation.

**Alternatives considered:**  
- Event study as main design (rejected: loses the continuous daily signal contribution).
- Event study as complement (acceptable but not required).

**Consequences:**  
The main design is expanding-window out-of-sample forecasting. Event studies may be mentioned as context but are not the core method.

**Revisit condition:**  
Not applicable — this is a fundamental design choice.

---

## 2026-06-28 — Salvage assessment of thesis_old_try before Phase 1

**Decision:**  
Audit `thesis_old_try/` to identify reusable raw data, code patterns, and reference material before deleting the folder. Defer deletion until salvage is complete.

**Reason:**  
The `thesis_old_try/` folder contains Bloomberg raw data (WAERLST, BSHIELDT), UAF attack data, GPR index, GDELT topic counts, ACLED data, SIPRI exposure data, and 15 processing scripts. These may contain reusable raw data and code patterns. However, the old attempt was a causal firm-level panel regression study, which is fundamentally different from the new predictive index-level forecasting design. Raw data may be reusable; old methodology and results are not.

**Alternatives considered:**  
- Delete `thesis_old_try/` immediately (rejected: would lose potentially valuable raw data).
- Keep `thesis_old_try/` indefinitely without audit (rejected: creates confusion and clutter).
- Copy everything to new structure without assessment (rejected: would import incompatible processed data and methodology).

**Consequences:**  
A new agent session will audit the folder and produce a salvage plan in `docs/thesis_old_try_audit.md`. Only after salvage is executed will the folder be deleted.

**Revisit condition:**  
After salvage is complete, verify nothing needed was lost before deletion.

---

## 2026-06-28 — Conservative timing: day t information predicts t+1

**Decision:**  
Use the conservative timing rule: information available through the end of day `t` predicts the market outcome on trading day `t+1`.

**Reason:**  
Ukrainian overnight attacks and morning reports may overlap with European trading hours. The conservative rule reduces ambiguity around publication times and overnight attacks.

**Alternatives considered:**  
- Same-day prediction with pre-market cutoff (rejected as primary: timing ambiguity; reserved as secondary).
- t+2 or longer (rejected: loses the main one-day-ahead forecast horizon).

**Consequences:**  
All features must have an "available at" timestamp ≤ end of day `t`. The primary forecast horizon is one trading day ahead.

**Revisit condition:**  
If precise timestamps allow a reliable pre-market cutoff for a secondary design.

---

## 2026-06-28 — Return units: percent, not decimal

**Decision:**  
All `r_*` columns in `data/processed/financial/financial_daily.parquet` are stored in **percent (%)**, not decimal.  For example, `r_ITA` daily std ≈ 1.67 means 1.67 %, not 0.0167.

**Reason:**  
Matches Bloomberg's terminal display convention and makes the columns human-readable without a multiplier.  The data dictionary and all downstream code must be aware of this convention to avoid unit-mismatch bugs (e.g., Sharpe ratios inflated by 100×).

**Alternatives considered:**  
- Store as decimal (rejected: easy to misread on screen, easy to forget to scale up in plots).
- Store both percent and decimal columns (rejected: doubles column count for negligible benefit).

**Consequences:**  
- All Phase 5-7 code that consumes `r_*` columns must treat them as percent.
- Any standardised decimal-return library (e.g. `empyrical`, `quantstats`) must divide by 100 first.
- Plots and tables should label axes as "Return (%)".

**Revisit condition:**  
If a downstream model absolutely requires decimal input and the conversion overhead becomes a recurring friction.

---

## 2026-06-28 — GKG country codes: dual mapping (ISO + GKG aliases)

**Decision:**  
`config/country_groups.yaml` maps **both** ISO 3166-1 alpha-2 codes (e.g. `UA`, `RU`, `DE`) **and** GKG-specific aliases (e.g. `UP`, `RS`, `GM`, `UK`, `EI`, `IS`, `JA`, `KS`) to the same source group.

**Reason:**  
GDELT GKG uses non-ISO codes in its `LOCATIONS` field for several countries (Ukraine = `UP` not `UA`, Russia = `RS` not `RU`, etc.).  A single-code mapping would miss every Ukrainian and Russian article.

**Alternatives considered:**  
- Normalise GKG codes to ISO before classification (rejected: adds a translation step and risks lossy mapping for codes with no ISO equivalent).
- Reject articles with non-ISO codes (rejected: would discard 100 % of Ukrainian and Russian coverage).

**Consequences:**  
- The hybrid classifier in `src/data/gdelt.py::classify_source_enhanced` handles both codes transparently.
- The country lookup is done in upper-case after `.str.strip()`.

**Revisit condition:**  
If GDELT changes its country-code scheme in a future GKG version.

---

## 2026-06-30 — Standardize `date` as the first regular column across all daily tables

**Decision:**  
All Phase 1-3 daily tables use a consistent schema: **`date` is the first regular column** (not the index).  `news_daily_enriched.parquet` already follows this convention after the Phase 3 gap-closure (`scripts/phase3_close_gaps.py`).  `financial_daily.parquet` and `attack_daily.parquet` still use `date` as the index and **will be re-written by Phase 5**.

**Reason:**  
Mixed index-vs-column conventions cause silent bugs in `merge()` and `join()` operations.  Standardising now (before any merge code is written) prevents a class of subtle errors that would be hard to debug later.

**Alternatives considered:**  
- Keep the index convention for all three (rejected: less pandas-idiomatic; harder to read CSV exports).
- Use a multi-index (`date`, `index_id`) (rejected: only one asset per row at the moment, multi-index would be overkill).

**Consequences:**  
Phase 5 (`src/data/merge.py`) will include a `standardize_date_column()` helper that does `df.reset_index()` if `date` is the index, then asserts `date` is the first column.

**Revisit condition:**  
Never — this is a permanent schema convention.

---

## 2026-06-30 — Automated precision check replaces manual audit

**Decision:**  
Replace the planned 400-article manual labelling audit (`data/processed/news/manual_precision_audit_enriched.csv`) with an **automated agreement check** against the high-confidence domain→country mapping.  The manual CSV is retained in the repo as a reference but is **not blocking** the thesis.

**Reason:**  
- The manual audit would label only 400 articles, providing weak statistical power.
- An automated check on 11 M+ articles with a high-confidence subset (6,480 domains, 31 % of total) provides more reliable precision estimates and runs in <1 min.
- The audit dataset's `title` column is empty (GKG bulk has no title), making manual labelling by URL alone significantly harder.

**Alternatives considered:**  
- Manual labelling of 400 articles (rejected: 2-4 h of human work, lower statistical power).
- Skip precision estimation entirely (rejected: needed to defend the classifier choice in the thesis).
- Hybrid: automated + spot-check 50 per group (~2 h) (deferred: can be added in Phase 8 robustness if needed).

**Consequences:**  
- `data/processed/news/auto_precision_report.md` is generated by `scripts/phase3_close_gaps.py` step 4.
- Per-method and per-group precision is reported (overall 85.4 %).
- The thesis documents the caveat that the precision is agreement with a data-driven proxy, not a hand-labelled ground truth.

**Revisit condition:**  
If a true labelled dataset (e.g., 50 articles per group hand-classified) becomes available, replace the proxy with the true estimate and report both for transparency.
