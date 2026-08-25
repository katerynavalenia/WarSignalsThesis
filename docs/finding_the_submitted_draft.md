# Which draft went to the supervisor?

**Date:** 2026-08-20

The draft is **not in this repository and never has been.** Checked across all
branches and the full history:

```
git log --all --pretty=format: --name-only | grep -iE 'thesis/|chapter|paper|draft'
  → thesis/chapters/.gitkeep
  → thesis_v1/thesis/chapters/.gitkeep
```

Only the placeholder. No `.docx`, `.tex`, `.pdf` or chapter file has ever been
committed. So the file is on Google Drive, on a laptop, or attached to the email
that went to Thomas — and the sent-mail attachment is the most reliable copy,
because it is by definition exactly what he read.

---

## 1. Where to look, in order

1. **Sent mail.** Search for the message to Thomas. The attachment is
   authoritative: it is the version he reviewed, timestamped by the send date.
2. **Google Drive**, sorted by *last modified*, filtered to documents. Also
   check Drive's own **version history** on the file (File → Version history):
   it often still holds the state as of the send date even if the file has been
   edited since.
3. **Laptop**, sorted by modification date, around the send date.
4. **Overleaf**, if any of it was written in LaTeX — it keeps full history.

## 2. How to tell which version you are holding

The repository can date a document from the numbers inside it. Find any of
these in the file and match:

### The GDELT corpus numbers

| If the draft says | It is |
|---|---|
| **11,433,653** articles after dedup (12,108,464 raw), **20,926** domains, 1,342 days, 2022-09-29 → 2026-06-21 | **final**, from 2026-06-30 onward |
| Tone: Ukrainian **−3.51**, Russian **−3.63**, Western **−1.87**, Other −0.17 | **final**, from 2026-06-30 |
| Tone: Ukrainian −4.12, Russian −3.89, Western −0.99 · or **259,898** articles | an early **3-month test run**, superseded — if the draft quotes these, it predates the full corpus |
| Source split: Western 84.9% / Other 6.9% / Russian 4.7% / Ukrainian 3.5% | **final**, from 2026-06-30 |

### The forecasting target — the sharpest divider

The primary target changed on **2026-07-02**.

| If the draft's primary target is | It is |
|---|---|
| **`r_ITA`** (a US ETF), with WAERLST/BSHIELDT only as *reconstructions* | **before 2026-07-02** |
| **`r_WAERLST`** (the real Bloomberg global A&D index), BSHIELDT as robustness | **2026-07-02 or later** — the last v1 state |

### Numbers unique to the final run (2026-07-02)

- Information-set sizes: **F = 37, P = 73, N = 63, PN = 115, PNG = 118**.
  (If the draft says N = F, or N = 21 and F = 23, it predates the N-info-set bug
  fix on 2026-07-02.)
- XGBoost, h = 1, `r_WAERLST`: MAE **0.9596** (F) → **0.9556** (PNG),
  directional accuracy **0.5513** → **0.5543**.
- `r_BSHIELDT` directional accuracy **0.5191**, identical across all five
  information sets — distinctive and easy to spot.
- Plain GARCH on `r_WAERLST`, h = 1: QLIKE **1.285**; EGARCH **1.267**.
- GARCH-X was numerically degenerate — **100%** of folds for BSHIELDT.

### Repository timeline for context

| Date | State |
|---|---|
| 2026-06-30 | Phase 3 GDELT corpus finalised (the tone and article numbers above) |
| 2026-07-01 | Phases 5, 6, 7 implemented; independent audit run |
| **2026-07-02** | **Real Bloomberg indices adopted; `r_WAERLST` becomes primary; N info-set bug fixed. This is the final v1 state.** |
| 2026-08-16 | Repository restructured into `thesis_v1/` + `thesis_v2/`; context files removed |

A draft written after 2026-07-02 and before the review should therefore quote
the WAERLST-primary numbers. If yours quotes ITA-primary numbers, it is an
earlier draft than the final results — worth knowing, because it means the
paper Thomas read may not reflect the last v1 run.

## 3. Once you find it — commit it

This gap is a process problem, not just an inconvenience. Put the draft under
version control so the question cannot recur:

```
thesis_v1/thesis/submitted/   ← the exact file sent to the supervisor, unedited
thesis_v1/thesis/             ← the working draft
```

`thesis_v1/thesis/submitted/` now exists for this purpose. Commit the file with
a message naming the send date, e.g.
`thesis: add the draft sent to the supervisor on YYYY-MM-DD`. `.docx` and `.pdf`
are binary and will not diff usefully, but git will still preserve every version
and its date — which is all that is needed here.

Then, when the reply comes, the review comments and the exact text they refer to
sit side by side in one history.
