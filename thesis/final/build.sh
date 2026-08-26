#!/usr/bin/env bash
# Build the final thesis PDF from thesis.tex.
#
#   ./build.sh            # writes thesis.pdf next to the source
#   ./build.sh /some/dir  # writes it somewhere else
#
# This directory is self-contained: thesis.tex, references.bib and figures/
# are everything the document needs. It can be zipped and uploaded to Overleaf
# as-is, with thesis.tex set as the main file.
#
# Three engines are tried in order and whichever is present is used:
#
#   tectonic   self-contained, downloads what it needs, no TeX install required
#   latexmk    the usual choice on a machine with TeX Live
#   pdflatex   with an explicit bibtex pass, for a minimal installation

set -euo pipefail
cd "$(dirname "$0")"

OUT="${1:-.}"
mkdir -p "$OUT"

if command -v tectonic >/dev/null 2>&1; then
  # Tectonic resolves the bibliography itself, so no separate bibtex pass.
  tectonic -X compile thesis.tex --outdir "$OUT"
elif command -v latexmk >/dev/null 2>&1; then
  latexmk -pdf -bibtex -outdir="$OUT" thesis.tex
elif command -v pdflatex >/dev/null 2>&1; then
  pdflatex -output-directory="$OUT" thesis.tex
  (cd "$OUT" && bibtex thesis) || true
  pdflatex -output-directory="$OUT" thesis.tex
  pdflatex -output-directory="$OUT" thesis.tex
else
  echo "No LaTeX engine found. Install one of:" >&2
  echo "  tectonic   https://tectonic-typesetting.github.io  (no TeX install needed)" >&2
  echo "  texlive    sudo apt install texlive-latex-recommended texlive-bibtex-extra" >&2
  exit 1
fi

PDF="$OUT/thesis.pdf"
[[ -f "$PDF" ]] || { echo "build produced no PDF" >&2; exit 1; }

# Fail loudly on the two failures that are easy to miss in a long log: a
# citation that never resolved, and a cross-reference left dangling. Both
# render as "[?]" or "??" in the text layer.
if command -v pdftotext >/dev/null 2>&1; then
  txt=$(mktemp); pdftotext -layout "$PDF" "$txt"
  bad=$(grep -c '\[?\]' "$txt" || true)
  if [[ "$bad" -gt 0 ]]; then
    echo "WARNING: $bad unresolved citation or reference marker(s) in $PDF" >&2
  else
    echo "all citations and cross-references resolved"
  fi
  rm -f "$txt"
fi

if command -v pdfinfo >/dev/null 2>&1; then
  echo "wrote $PDF ($(pdfinfo "$PDF" | awk '/^Pages/{print $2}') pages)"
else
  echo "wrote $PDF"
fi
