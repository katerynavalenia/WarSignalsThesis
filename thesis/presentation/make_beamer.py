"""Emit ``slides.tex`` from the content spine, for ``defence.tex`` to input.

Run from anywhere::

    python thesis/presentation/make_beamer.py

The preamble lives in ``defence.tex`` and is hand-written; only the frames are
generated. Tables are set with ``tabularx`` so that the label column wraps
rather than running into the margin --- a slide has no margin to spare, and
``\\resizebox`` would leave each table at a different type size.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import slides as content                        # noqa: E402
from markup import escape_plain, to_latex       # noqa: E402

HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "slides.tex"

# Beamer's body size, chosen per slide from how much text the slide carries and
# from how much of the frame the exhibit has already taken. Stepping the whole
# frame is more legible than shrinking individual bullets, and sizing here is
# what keeps the frames off beamer's [shrink] option, which rescales a frame to
# whatever fits and so leaves no two slides at the same type size.
def _body_size(item: content.Slide) -> str:
    chars = sum(len(b.text) for b in item.bullets)
    if item.table is not None:
        # The table has the top of the frame and the bullets take what is
        # left, but never below \scriptsize: \tiny is 6pt at this base size,
        # which does not read from the back of a room. If a table slide
        # overflows at this size the bullets are too long, and the fix is to
        # shorten them rather than to shrink them.
        return r"\scriptsize"
    if item.figure:
        # A figure claims roughly two fifths of the frame on its own.
        return r"\scriptsize" if chars > 550 else r"\footnotesize"
    if chars > 1500:
        return r"\scriptsize"
    if chars > 1050:
        return r"\footnotesize"
    if chars > 700:
        return r"\small"
    return r"\normalsize"


def _table_size(table: content.Table) -> str:
    if len(table.rows) > 9 or len(table.headers) > 5:
        return r"\tiny"
    return r"\scriptsize"


# A 16:9 beamer frame at 11pt measures 404pt across and 252pt down, and the
# frame title takes about 40pt of that. The exhibits are roughly 2:1, so one at
# full width would be 202pt tall and leave no room for a single line of text.
# These fractions give the figure the bulk of what remains after three short
# bullets; the bullets on figure slides are kept to one line each for exactly
# this reason, with the detail moved into the speaker notes.
def _figure_box(item: content.Slide) -> tuple[str, str]:
    """Width and height caps for the figure, as fractions. Whichever binds."""
    chars = sum(len(b.text) for b in item.bullets)
    if chars > 300:
        return "0.72", "0.45"
    return "0.78", "0.50"


def _is_group_row(row: list[str]) -> bool:
    return bool(row[0]) and all(not cell for cell in row[1:])


def _colspec(aligns: str) -> str:
    """``l`` columns wrap and share the slack; ``c`` and ``r`` stay tight."""
    return "".join({"l": "L", "c": "c", "r": "r"}[a] for a in aligns)


def _render_table(table: content.Table) -> list[str]:
    n = len(table.headers)
    out = [
        r"\begin{center}",
        _table_size(table),
        r"\setlength{\tabcolsep}{4pt}",
        r"\renewcommand{\arraystretch}{1.12}",
        r"\begin{tabularx}{\linewidth}{" + _colspec(table.alignment()) + "}",
        r"\toprule",
    ]
    heads = " & ".join(rf"\textbf{{{to_latex(h)}}}" if h else "" for h in table.headers)
    out += [heads + r" \\", r"\midrule"]

    for i, row in enumerate(table.rows):
        if _is_group_row(row):
            out.append(rf"\multicolumn{{{n}}}{{@{{}}l}}{{\itshape {to_latex(row[0])}}} \\")
        else:
            out.append(" & ".join(to_latex(c) for c in row) + r" \\")
        if i in table.rules_after:
            out.append(r"\addlinespace[2pt]")
    out += [r"\bottomrule", r"\end{tabularx}", r"\end{center}"]

    if table.note:
        out += [
            r"\vspace{-0.4em}",
            r"{\tiny\color{deckmuted}\textit{Notes:} " + to_latex(table.note) + r"\par}",
        ]
    return out


def _render_bullets(bullets: list[content.Bullet]) -> list[str]:
    out = [r"\begin{itemize}"]
    depth = 0
    for bullet in bullets:
        while depth < bullet.level:
            out.append(r"\begin{itemize}")
            depth += 1
        while depth > bullet.level:
            out.append(r"\end{itemize}")
            depth -= 1
        out.append(r"\item " + to_latex(bullet.text))
    while depth > 0:
        out.append(r"\end{itemize}")
        depth -= 1
    out.append(r"\end{itemize}")
    return out


def _render_figure(item: content.Slide) -> list[str]:
    # The height cap is what keeps a wide figure from pushing the caption off
    # the bottom of the frame; keepaspectratio makes whichever bound binds.
    width, height = _figure_box(item)
    out = [
        r"\vspace{-0.35em}",
        r"\begin{center}",
        rf"\includegraphics[width={width}\linewidth,height={height}\textheight,"
        + r"keepaspectratio]{figures/" + item.figure + "}",
    ]
    if item.caption:
        out += [
            r"\\[0.2em]",
            r"{\tiny\color{deckmuted}" + to_latex(item.caption) + r"\par}",
        ]
    out.append(r"\end{center}")
    return out


def _render_title(item: content.Slide) -> list[str]:
    return [
        r"\begin{frame}[plain]",
        r"\vspace{1.6em}",
        r"{\color{deckaccent}\rule{\linewidth}{2pt}}\par\vspace{2.2em}",
        r"{\usebeamerfont{title}\color{deckink}\bfseries " + to_latex(item.title) + r"\par}",
        r"\vspace{0.9em}",
        r"{\large\color{deckaccent}" + to_latex(item.subtitle) + r"\par}",
        r"\vspace{1.8em}",
        r"{\color{deckrule}\rule{0.28\linewidth}{0.8pt}}\par",
        r"\vspace{0.9em}",
        r"{\large\color{deckink}" + to_latex(item.author) + r"\par}",
        r"\vspace{0.35em}",
        r"{\small\color{deckmuted}" + to_latex(item.date) + r"\par}",
        r"\end{frame}",
    ]


def _render(item: content.Slide) -> list[str]:
    if item.kind == "title":
        out = _render_title(item)
    else:
        out = [
            r"\renewcommand{\slidesection}{" + to_latex(item.section) + "}",
            r"\begin{frame}{" + to_latex(item.title) + "}",
            _body_size(item),
        ]
        if item.table is not None:
            out += _render_table(item.table)
            if item.bullets:
                out.append(r"\vspace{0.3em}")
                out += _render_bullets(item.bullets)
        elif item.figure:
            if item.bullets:
                out += _render_bullets(item.bullets)
            out += _render_figure(item)
        else:
            out += _render_bullets(item.bullets)
        out.append(r"\end{frame}")

    if item.notes:
        out.append(r"\note{" + escape_plain(item.notes) + "}")
    return out


def build() -> Path:
    lines = [
        "% Generated by make_beamer.py from slides.py --- do not edit by hand.",
        "% Edit thesis/presentation/slides.py and rebuild.",
        "",
    ]
    for item in content.MAIN:
        lines += _render(item)
        lines.append("")

    lines += [
        r"\appendix",
        r"\renewcommand{\slidesection}{Backup}",
        r"\begin{frame}[plain]",
        r"\vspace{2.5em}",
        r"{\color{deckaccent}\rule{\linewidth}{2pt}}\par\vspace{1.5em}",
        r"{\usebeamerfont{title}\color{deckink}\bfseries Backup slides\par}",
        r"\vspace{0.6em}",
        r"{\color{deckmuted}Held for questions.\par}",
        r"\end{frame}",
        "",
    ]
    for item in content.BACKUP_SLIDES:
        lines += _render(item)
        lines.append("")

    OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return OUTPUT


if __name__ == "__main__":
    path = build()
    print(f"wrote {path} ({len(content.MAIN)} main + {len(content.BACKUP_SLIDES)} backup frames)")
