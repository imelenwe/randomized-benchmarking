#!/usr/bin/env bash
# Regenerate CB_Report.pdf from CB_report.md.
# Run from anywhere; cd's into reports/ itself.
set -euo pipefail
cd "$(dirname "$0")"
export PATH="$HOME/Library/TinyTeX/bin/universal-darwin:$PATH"
PANDOC="${PANDOC:-/opt/anaconda3/bin/pandoc}"

echo "→ rendering CB_Report.pdf (xelatex)"
"$PANDOC" CB_report.md \
  --pdf-engine=xelatex \
  --from markdown \
  -o CB_Report.pdf

echo "Done."
ls -la CB_Report.pdf
