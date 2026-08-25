#!/usr/bin/env bash
# Build the thesis from the markdown chapters.
#
#   ./build.sh pdf    -> thesis.pdf   (needs pandoc + a LaTeX engine)
#   ./build.sh tex    -> thesis.tex   (needs pandoc only; upload this to Overleaf)
#   ./build.sh docx   -> thesis.docx  (needs pandoc only)
#
# VERIFIED with pandoc 3.1.11 on 2026-08-25: `tex` and `docx` both build clean
# from a bare checkout of the chapters. The tex output carries 9 chapters, 3
# figures, 54 tables and all 16 bibliography entries, so the citeproc and
# resource-path settings below are known good rather than assumed.
#
# `pdf` is the one target still unverified here, because it needs a LaTeX engine
# and none is installed on this machine. The tex target is the safe route: build
# it and upload to Overleaf.
#
# Install on Debian/Ubuntu:
#   sudo apt install pandoc texlive-xetex texlive-fonts-recommended
# Or skip LaTeX entirely: build `tex` and upload thesis.tex, references.bib and
# the figures directory to Overleaf.

set -euo pipefail
cd "$(dirname "$0")"

TARGET="${1:-pdf}"

# Order matters. 00_outline_and_numbers.md is the assembly map, not a chapter,
# and README.md is the index -- neither goes into the document.
CHAPTERS=(
  01_introduction.md
  02_literature.md
  03_data.md
  04_measurement.md
  05_stylized_facts.md
  06_response.md
  07_efficiency.md
  08_robustness.md
  09_conclusion.md
)

for f in "${CHAPTERS[@]}"; do
  [[ -f "$f" ]] || { echo "missing chapter: $f" >&2; exit 1; }
done

command -v pandoc >/dev/null || {
  echo "pandoc not found. See the install line at the top of this script." >&2
  exit 1
}

COMMON=(
  --from=markdown+smart+pipe_tables+tex_math_dollars
  --metadata-file=metadata.yaml
  --citeproc
  --resource-path=.:..
  --top-level-division=chapter
)

case "$TARGET" in
  pdf)
    # xelatex handles the Cyrillic domain names (24tv.ua is fine, but outlet
    # names elsewhere are not) and en-dashes without a preamble fight.
    pandoc "${COMMON[@]}" --pdf-engine=xelatex \
      -V mainfont="DejaVu Serif" -V monofont="DejaVu Sans Mono" \
      "${CHAPTERS[@]}" -o thesis.pdf
    echo "wrote thesis.pdf"
    ;;
  tex)
    pandoc "${COMMON[@]}" --standalone "${CHAPTERS[@]}" -o thesis.tex
    echo "wrote thesis.tex -- upload with references.bib and ../outputs/figures/ to Overleaf"
    ;;
  docx)
    pandoc "${COMMON[@]}" "${CHAPTERS[@]}" -o thesis.docx
    echo "wrote thesis.docx"
    ;;
  *)
    echo "usage: $0 [pdf|tex|docx]" >&2
    exit 1
    ;;
esac

# Problems to expect only on the `pdf` target, which is the untested one. The
# `tex` and `docx` targets were run and produced correct output; if one of these
# bites you there, something in the tree has changed since:
#
# 1. Figure paths. The chapters reference ../outputs/figures/*.png, which is
#    correct relative to this directory. --resource-path covers it; if a figure
#    still fails to resolve, pass --resource-path=.:..:../outputs.
#
# 2. Missing fonts. If DejaVu is absent, drop the two -V font flags and let
#    xelatex choose, or install texlive-fonts-recommended.
#
# 3. References empty. metadata.yaml sets `nocite: @*` so every bib entry
#    appears even though the chapters cite in prose. If the list comes out
#    empty, check that references.bib is beside this script and that pandoc was
#    built with citeproc (pandoc 2.11+).
#
# 4. Chapter headings. Each file starts with a level-1 heading, and
#    --top-level-division=chapter maps those to \chapter. If they come out as
#    \section, the flag was dropped.
