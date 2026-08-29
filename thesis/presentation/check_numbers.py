"""Verify the deck against the submitted manuscript.

Two checks, both of which have to pass before the deck is presentable.

**Every number traces back.** Each numeric token appearing anywhere on a slide
--- bullet, table cell, caption or speaker note --- must also appear in
``thesis/final/thesis.tex``, which was itself checked against
``outputs/tables/`` on 2026-08-26. Anything that does not is either a
transcription error or a number the deck invented, and both are reportable.

**No retracted claim is presented as live.** Six results in this project were
significant and were retracted (``docs/findings_status.md``). They may appear
on the two slides that exist to report them as failures, and nowhere else.

Run directly, or as the last step of ``build.sh``::

    python thesis/presentation/check_numbers.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import slides as content            # noqa: E402
from markup import to_plain         # noqa: E402

HERE = Path(__file__).resolve().parent
THESIS = HERE.parent / "final" / "thesis.tex"

# Numbers that are legitimately absent from thesis.tex. Each needs a reason;
# an entry without one is how a wrong number gets waved through.
ALLOWED: dict[str, str] = {
    "48": (
        "The thesis spells this one out --- 'Forty-eight augmented HAR-RV-X "
        "specifications' (Section 4.4) --- and Table 10 gives it as 4 blocks "
        "of 12. docs/findings_status.md writes it as 48."
    ),
}

# Phrases that would state a retracted result as a live one. A slide may use
# one only while disclaiming it: the six retracted results are reportable as
# failures and as nothing else.
RETRACTION_MARKERS = ("censorship wedge", "state-versus-independent")

# Words that mark a mention as a disclaimer rather than a claim. Requiring one
# in the same sentence is what lets the tone slide say the comparison "does not
# survive and is not claimed" while still catching an affirmative use.
DISCLAIMERS = (
    "not claimed", "does not survive", "did not survive", "retracted",
    "eliminated", "correcting", "dissolved", "further from significance",
)

_NUMBER = re.compile(r"\d+(?:\.\d+)?")


def _numbers(text: str) -> set[str]:
    """Numeric tokens, thousands separators removed so 4,027 matches 4027."""
    return set(_NUMBER.findall(text.replace(",", "").replace(" ", "")))


def _slide_text(item: content.Slide) -> str:
    parts = [item.title, item.subtitle, item.caption, item.notes]
    parts += [b.text for b in item.bullets]
    if item.table is not None:
        parts += item.table.headers
        parts += [cell for row in item.table.rows for cell in row]
        parts.append(item.table.note)
    return "\n".join(to_plain(p) for p in parts if p)


def main() -> int:
    if not THESIS.exists():
        print(f"FAIL: cannot find the manuscript at {THESIS}")
        return 1

    thesis_numbers = _numbers(THESIS.read_text(encoding="utf-8"))

    problems: list[str] = []
    checked = 0

    for item in content.DECK:
        text = _slide_text(item)
        for number in sorted(_numbers(text)):
            checked += 1
            if number in thesis_numbers or number in ALLOWED:
                continue
            problems.append(f"  {item.title!r}: {number} is not in thesis.tex")

        for marker in RETRACTION_MARKERS:
            for sentence in re.split(r"(?<=[.;])\s+", text):
                low = sentence.lower()
                if marker in low and not any(d in low for d in DISCLAIMERS):
                    problems.append(
                        f"  {item.title!r}: states {marker!r} without disclaiming it "
                        f"--- that result is retracted:\n      {sentence.strip()}"
                    )

    # The retraction slide must actually name what killed each result: a row
    # with an empty second column would present a retracted finding unopposed.
    dissolved = content.SIX_DISSOLVED.table
    assert dissolved is not None
    if len(dissolved.rows) != 6:
        problems.append(f"  the dissolved-results table has {len(dissolved.rows)} rows, expected 6")
    for row in dissolved.rows:
        if not row[1].strip():
            problems.append(f"  dissolved result {row[0]!r} has no eliminating test named")

    if problems:
        print(f"check_numbers: {len(problems)} problem(s)")
        print("\n".join(problems))
        return 1

    print(
        f"check_numbers: OK --- {checked} numeric references across "
        f"{len(content.DECK)} slides all trace to thesis.tex; "
        f"no retracted claim stated as live"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
