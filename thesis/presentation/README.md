# The defence deck

Two artefacts, one source. `defence.pptx` is the editable deck; `defence.pdf`
is the one to present from. Both are generated from
[`slides.py`](slides.py), so they cannot drift apart.

```bash
bash thesis/presentation/build.sh          # writes both, beside the source
```

The deck is built from **`thesis/final/thesis.pdf`**, the submission draft.
Note that `Zaichenko Kateryna Master Thesis.pdf` in the repository root is a
different author's thesis, kept as a benchmark — it is not a source for
anything here.

## What is in it

18 main slides for a **10–15 minute** slot, plus 7 backup slides for
questions. The structure follows the one used at the intermediate
presentation:

| Slides | Section |
|---|---|
| 1–2 | Title, roadmap |
| 3–4 | **Why this topic** — the repricing, then the literature and the gap |
| 5 | **Research question and contribution** |
| 6–8 | **Data sources and sample** — the measurement problem, the five ecosystems, the variables |
| 9 | **Identification strategy and model** |
| 10–14 | **Results** — two descriptive slides, then Gates 2/3, Gates 4/5, out of sample |
| 15 | **Findings** |
| 16–17 | **Robustness** — the battery, then the six results that dissolved |
| 18 | **Conclusions** |
| B1–B7 | **Backup** — Table 4 estimated, classification sensitivity, the market control, Clark–West vs DM, both forecasting races, the firm-level panel |

**If the slot turns out to be ten minutes**, drop the three slides named in
`TEN_MINUTE_CUT` at the foot of `slides.py`: the roadmap, *Variables, targets
and sample* (fold the sample size into the ecosystems slide), and *Robustness:
the tests that could have overturned this*. That leaves 15.

Every slide carries **speaker notes**. They hold the sentences that make each
number defensible — that the single surviving Gate 2 cell sits in a
pre-invasion window, that power is not exclusion, that Gate 2 was never
pre-registered. To get them out of the PDF, uncomment one line near the foot of
[`defence.tex`](defence.tex): `\setbeameroption{show notes}` for interleaved
note pages, or `show notes on second screen=right` for a presenter display. In
PowerPoint they are already in the notes pane.

## Editing

**Edit [`slides.py`](slides.py) and rebuild.** Do not edit `slides.tex` — it is
generated and will be overwritten. Editing `defence.pptx` by hand is fine if
you are finishing the deck by hand, but a rebuild overwrites that too.

The authoring markup is plain text plus three things: `**bold**`, `*italic*`
and `$LaTeX maths$`. Everything else is literal — write `%` and `&`, not `\%`
and `\&`. [`markup.py`](markup.py) is the only file that knows how each output
format spells those, and it renders maths into unicode for PowerPoint, which
has no formula engine that survives a round trip through Keynote or Slides.

Sizing is automatic and deliberate. `make_beamer.py` steps the whole frame
down a size at a time rather than using beamer's `[shrink]`, which rescales
each frame to whatever fits and leaves no two slides at the same type size.
Table slides are pinned at `\scriptsize` and never `\tiny`: if a table slide
overflows, **shorten the bullets rather than shrink them** — 6pt does not read
from the back of a room. The same applies to the figure slides, whose bullets
are kept to one line each so the exhibit has room; the detail belongs in the
speaker notes.

## The check that matters

[`check_numbers.py`](check_numbers.py) runs as the last step of `build.sh` and
does two things.

1. **Every numeric token on every slide must appear in
   `thesis/final/thesis.tex`** — 278 of them at the last build. A number that
   does not appear is either a transcription error or one the deck invented.
   Legitimate exceptions go in `ALLOWED` *with a reason*; there is one, and it
   is there because the thesis spells "forty-eight" out in words.
2. **No retracted claim is stated as live.** Six results in this project were
   significant and were retracted — see
   [`docs/findings_status.md`](../../docs/findings_status.md). They appear on
   the deck only on *Six results that dissolved* and *Why the regional market
   control is decisive*, and only as failures. The check flags a mention that
   is not accompanied by a disclaimer.

Two conventions the deck inherits from the manuscript, and which an edit
should not blur:

- **Gates 3, 4 and 5 are pre-registered; Gate 2 is not.** The thesis invites
  the reader to verify this from commit timestamps, so the deck must not
  present Gate 2 as confirmatory.
- **Power is quoted at both sample lengths, never as one number** — 81% on the
  three long-sample targets and 44% on the two Bloomberg ones. And power is
  not exclusion.

## Requirements

`python-pptx` (in `requirements.txt`) for the .pptx, and a TeX Live install
with `beamer`, `booktabs`, `tabularx` and `appendixnumberbeamer` for the PDF.
The metropolis theme is deliberately *not* used — it is absent from a Debian
TeX Live base install, so the deck is styled by hand on the default theme
instead. Maths is set in Latin Modern serif via `\usefonttheme[onlymath]{serif}`
because beamer's sans maths font has no glyph for `\Delta`, which the
descriptive tables need on every row, and it renders as a black box rather
than warning.

In a git worktree, where `bootstrap.sh` has not created `.venv`, point the
build at an interpreter that has `python-pptx`:

```bash
PYTHON=/path/to/.venv/bin/python bash thesis/presentation/build.sh
```

## Regenerating the figures

The three PNGs in `figures/` are copies of the ones in
`thesis/final/figures/`, so this directory stays self-contained the way
`thesis/final/` does. `build.sh` re-copies any that are newer upstream. To
rebuild them from data, run `python scripts/plot_thesis_figures.py` first.
