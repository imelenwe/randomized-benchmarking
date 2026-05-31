#!/usr/bin/env bash
# Regenerate CB_Report.pdf from CB_report.md.
# Run from anywhere; cd's into reports/ itself.
#
# Two-step build: pandoc → .tex, post-process longtable → tabular (so tables
# stay atomic on a page), then xelatex.
set -euo pipefail
cd "$(dirname "$0")"
export PATH="$HOME/Library/TinyTeX/bin/universal-darwin:$PATH"
PANDOC="${PANDOC:-/opt/anaconda3/bin/pandoc}"

TEX="CB_report_build.tex"
trap 'rm -f "$TEX" "${TEX%.tex}".log "${TEX%.tex}".aux "${TEX%.tex}".out' EXIT

echo "→ pandoc: markdown → tex"
"$PANDOC" CB_report.md \
  --from markdown \
  --standalone \
  -o "$TEX"

echo "→ post-process: longtable → tabular (keep-together)"
python3 - "$TEX" <<'PY'
import re, sys, pathlib
p = pathlib.Path(sys.argv[1])
src = p.read_text()

# Walk through, find each \begin{longtable}[...]{...} with balanced braces,
# replace with a centered tabular wrapped in a non-breaking minipage.
def convert_longtables(text):
    out = []
    i = 0
    needle = r'\begin{longtable}'
    while True:
        j = text.find(needle, i)
        if j < 0:
            out.append(text[i:])
            break
        out.append(text[i:j])
        i = j + len(needle)
        # optional [opts]
        if i < len(text) and text[i] == '[':
            close = text.find(']', i)
            i = close + 1
        # required {colspec} — balance braces
        assert text[i] == '{', f"expected {{ at pos {i}: {text[i:i+40]!r}"
        depth = 0
        start = i
        while i < len(text):
            c = text[i]
            if c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    i += 1
                    break
            i += 1
        cols = text[start+1:i-1]
        # Clean longtable-specific bits from colspec
        cols = cols.replace('@{}', '').strip()
        # Replace \linewidth with \linewidth (no-op) — keep as-is; tabular
        # honors p{...} widths just like longtable.
        out.append('\\par\\medskip\\noindent\\begin{minipage}{\\linewidth}\\centering\\begin{tabular}{' + cols + '}')
    return ''.join(out)

src = convert_longtables(src)
# In pandoc's longtable layout, \bottomrule lives in the \endlastfoot block
# (between \endhead and \endlastfoot) so it's drawn at the end of the LAST
# page. In a plain tabular it would render at the wrong vertical position
# (right under the header). Strip the misplaced \bottomrule together with
# \endlastfoot, then re-emit \bottomrule just before \end{tabular}.
src = re.sub(r'\\bottomrule\\noalign\{\}\s*\\endlastfoot\s*', '', src)
src = re.sub(r'\\endlastfoot\s*', '', src)
for cmd in (r'\endfirsthead', r'\endhead', r'\endfoot'):
    src = re.sub(re.escape(cmd) + r'\s*', '', src)
src = src.replace(r'\end{longtable}', r'\bottomrule\noalign{}\end{tabular}\end{minipage}\par\medskip')

p.write_text(src)
print(f"  post-processed {p}")
PY

echo "→ xelatex (pass 1)"
xelatex -interaction=nonstopmode "$TEX" > "${TEX%.tex}.log" 2>&1 \
  || { tail -40 "${TEX%.tex}.log"; exit 1; }
echo "→ xelatex (pass 2 — resolve refs)"
xelatex -interaction=nonstopmode "$TEX" > "${TEX%.tex}.log" 2>&1 \
  || { tail -40 "${TEX%.tex}.log"; exit 1; }

mv "${TEX%.tex}.pdf" CB_Report.pdf

echo "Done."
ls -la CB_Report.pdf
