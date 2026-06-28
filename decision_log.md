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
