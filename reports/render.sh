#!/usr/bin/env bash
# Regenerate CB_Report_latex.pdf and CB_report_latex.html from CB_report_latex.md.
# Run from anywhere; cd's into reports/ itself.
set -euo pipefail
cd "$(dirname "$0")"
export PATH="$HOME/Library/TinyTeX/bin/universal-darwin:$PATH"
PANDOC="${PANDOC:-/opt/anaconda3/bin/pandoc}"

echo "→ rendering CB_Report_latex.pdf (xelatex)"
"$PANDOC" CB_report_latex.md \
  --pdf-engine=xelatex \
  --from markdown \
  -o CB_Report_latex.pdf

echo "→ rendering CB_report_latex.html (MathJax)"
"$PANDOC" CB_report_latex.md \
  --standalone --embed-resources --mathjax \
  --metadata title="Cycle Benchmarking — Part A + Part B Report" \
  --css /tmp/cb_print.css \
  --from markdown \
  -o CB_report_latex.html

echo "Done. Artifacts:"
ls -la CB_Report_latex.pdf CB_report_latex.html
