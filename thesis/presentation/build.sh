#!/usr/bin/env bash
# Build both halves of the defence deck from thesis/presentation/slides.py.
#
#   bash thesis/presentation/build.sh
#
# Writes defence.pptx and defence.pdf beside the source. Follows the same
# fallback order as thesis/final/build.sh: latexmk if it is there, otherwise
# two pdflatex passes (beamer needs the second to settle the frame count in
# the footline).
set -euo pipefail

cd "$(dirname "$0")"

# The repository venv, if it exists; otherwise whatever python is on the path.
# PYTHON= in the environment overrides both, which is what a git worktree needs
# since bootstrap.sh creates .venv only in the main checkout.
if [ -z "${PYTHON:-}" ]; then
    PYTHON="../../.venv/bin/python"
    [ -x "$PYTHON" ] || PYTHON="$(command -v python3 || command -v python)"
fi

if ! "$PYTHON" -c "import pptx" 2>/dev/null; then
    echo "error: python-pptx is not installed for $PYTHON" >&2
    echo "       run: pip install python-pptx   (it is in requirements.txt)" >&2
    echo "       or:  PYTHON=/path/to/venv/bin/python bash build.sh" >&2
    exit 1
fi

echo "==> figures"
# The deck reads its own copies so the directory stays self-contained, the
# same convention thesis/final/ follows.
for fig in fig1_defense_indices.png fig1_attention_full_sample.png fig2_tone_full_sample.png; do
    if [ ../final/figures/"$fig" -nt figures/"$fig" ] 2>/dev/null; then
        cp ../final/figures/"$fig" figures/"$fig"
        echo "    refreshed $fig"
    fi
done

echo "==> defence.pptx"
"$PYTHON" make_pptx.py

echo "==> slides.tex"
"$PYTHON" make_beamer.py

echo "==> defence.pdf"
if command -v latexmk >/dev/null 2>&1; then
    latexmk -pdf -quiet -interaction=nonstopmode defence.tex >/dev/null
else
    for pass in 1 2; do
        pdflatex -interaction=nonstopmode -halt-on-error defence.tex >/dev/null \
            || { echo "pdflatex failed on pass $pass; see defence.log"; exit 1; }
    done
fi

echo "==> checks"
if grep -q "Overfull" defence.log 2>/dev/null; then
    echo "    WARNING: overfull boxes -- a frame is running past its margin:"
    grep -c "Overfull" defence.log | sed 's/^/      count: /'
fi
if grep -qE "LaTeX Warning: (Reference|Citation)" defence.log 2>/dev/null; then
    echo "    WARNING: unresolved reference or citation"
fi

"$PYTHON" check_numbers.py

echo
echo "defence.pptx and defence.pdf are ready."
