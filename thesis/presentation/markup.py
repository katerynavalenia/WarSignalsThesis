"""Turn the deck's authoring markup into PowerPoint runs and into LaTeX.

``slides.py`` is written once, in a plain-text markup with ``**bold**``,
``*italic*`` and ``$maths$``. This module is the only place that knows how
either output format spells those, so a rendering bug is fixed in one place
rather than two.

The LaTeX direction has to escape; the PowerPoint direction has to render
maths into unicode, because a .pptx has no formula engine that survives a
round trip through Keynote or Google Slides.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Segmentation
# ---------------------------------------------------------------------------

# Maths first, so that a $...$ span is never split by a ** inside it, then
# bold, then italic. The single-asterisk pattern requires a non-space after the
# opening marker so that a literal asterisk cannot open an emphasis run.
_TOKEN = re.compile(
    r"(?P<math>\$[^$]+\$)"
    r"|(?P<bold>\*\*.+?\*\*)"
    r"|(?P<italic>\*(?=\S).+?\*)"
)


@dataclass
class Run:
    text: str
    bold: bool = False
    italic: bool = False
    math: bool = False


def segment(text: str, bold: bool = False, italic: bool = False) -> list[Run]:
    """Split authored markup into runs, preserving order.

    Emphasis and maths nest: ``**$-1.66$**`` is a bold maths run, which is the
    common case on the descriptive slides, so the contents of a bold or italic
    span are segmented again rather than taken as literal text.
    """
    runs: list[Run] = []
    pos = 0
    for m in _TOKEN.finditer(text):
        if m.start() > pos:
            runs.append(Run(text[pos:m.start()], bold=bold, italic=italic))
        if m.group("math"):
            runs.append(Run(m.group("math")[1:-1], bold=bold, italic=italic, math=True))
        elif m.group("bold"):
            runs.extend(segment(m.group("bold")[2:-2], bold=True, italic=italic))
        else:
            runs.extend(segment(m.group("italic")[1:-1], bold=bold, italic=True))
        pos = m.end()
    if pos < len(text):
        runs.append(Run(text[pos:], bold=bold, italic=italic))
    return runs


# ---------------------------------------------------------------------------
# LaTeX
# ---------------------------------------------------------------------------

# Order matters: the backslash must be replaced first, and the dash and quote
# forms must not be re-escaped afterwards.
_LATEX_ESCAPES = [
    ("\\", r"\textbackslash{}"),
    ("&", r"\&"),
    ("%", r"\%"),
    ("$", r"\$"),
    ("#", r"\#"),
    ("_", r"\_"),
    ("{", r"\{"),
    ("}", r"\}"),
    ("~", r"\textasciitilde{}"),
    ("^", r"\textasciicircum{}"),
    ("€", r"\texteuro{}"),
    ("“", "``"),
    ("”", "''"),
    ("’", "'"),
]


def _escape_latex(text: str) -> str:
    for old, new in _LATEX_ESCAPES:
        text = text.replace(old, new)
    return text


def to_latex(text: str) -> str:
    """Render authored markup as LaTeX body text."""
    out = []
    for run in segment(text):
        # Maths is authored as LaTeX already, so it is passed through rather
        # than escaped; emphasis still wraps it.
        body = f"${run.text}$" if run.math else _escape_latex(run.text)
        if run.bold:
            body = f"\\textbf{{{body}}}"
        if run.italic:
            body = f"\\emph{{{body}}}"
        out.append(body)
    return "".join(out)


# ---------------------------------------------------------------------------
# Maths to unicode, for PowerPoint
# ---------------------------------------------------------------------------

_SYMBOLS = {
    r"\times": "\u00d7",
    r"\cdot": "\u00b7",
    r"\approx": "\u2248",
    r"\rightarrow": "\u2192",
    r"\leq": "\u2264",
    r"\geq": "\u2265",
    r"\alpha": "\u03b1",
    r"\beta": "\u03b2",
    r"\gamma": "\u03b3",
    r"\Delta": "\u0394",
    r"\varepsilon": "\u03b5",
    r"\epsilon": "\u03b5",
    r"\sim": "~",
    r"\,": " ",
    r"\;": " ",
}

_SUPERSCRIPT = str.maketrans("0123456789+-=()n", "\u2070\u00b9\u00b2\u00b3\u2074\u2075\u2076\u2077\u2078\u2079\u207a\u207b\u207c\u207d\u207e\u207f")
_SUBSCRIPT = str.maketrans("0123456789+-=()", "\u2080\u2081\u2082\u2083\u2084\u2085\u2086\u2087\u2088\u2089\u208a\u208b\u208c\u208d\u208e")


def _script(body: str, table: dict[int, int], marker: str) -> str:
    """Unicode super/subscript where every character has one, else a marker.

    Significance stars are the one case that reads better without either:
    ``0.925^{***}`` becomes ``0.925***``, which is how a table would print it.
    """
    if body and set(body) == {"*"}:
        return body
    # Letters other than ``n`` have no unicode script form, so a subscript like
    # ``_{Local}`` falls back to the flat ``_Local``.
    if any(ch.isalpha() and ch != "n" for ch in body):
        return marker + body
    return body.translate(table)


def to_unicode(math: str) -> str:
    """Render a LaTeX maths fragment into plain unicode for a .pptx run."""
    text = math
    for tex, glyph in _SYMBOLS.items():
        text = text.replace(tex, glyph)
    text = re.sub(r"\\text\{([^}]*)\}", r"\1", text)
    text = re.sub(r"\^\{([^}]*)\}", lambda m: _script(m.group(1), _SUPERSCRIPT, "^"), text)
    text = re.sub(r"_\{([^}]*)\}", lambda m: _script(m.group(1), _SUBSCRIPT, "_"), text)
    text = re.sub(r"\^(\w)", lambda m: _script(m.group(1), _SUPERSCRIPT, "^"), text)
    text = re.sub(r"_(\w)", lambda m: _script(m.group(1), _SUBSCRIPT, "_"), text)
    text = text.replace("-", "\u2212")                 # proper minus sign
    return text.replace("{", "").replace("}", "").strip()


# ---------------------------------------------------------------------------
# PowerPoint
# ---------------------------------------------------------------------------

def _dashes(text: str) -> str:
    """LaTeX dash conventions, which PowerPoint has to spell out."""
    return text.replace("---", "\u2014").replace("--", "\u2013")


def to_runs(text: str) -> list[Run]:
    """Authored markup as PowerPoint-ready runs, maths already flattened."""
    out = []
    for run in segment(text):
        if run.math:
            out.append(Run(to_unicode(run.text), bold=run.bold, italic=run.italic))
        else:
            out.append(Run(_dashes(run.text), bold=run.bold, italic=run.italic))
    return out


def to_plain(text: str) -> str:
    """Markup stripped to bare text, for speaker notes and the number check."""
    return "".join(r.text for r in to_runs(text))


def escape_plain(text: str) -> str:
    """Escape prose that carries no markup, such as speaker notes."""
    return _escape_latex(text)
