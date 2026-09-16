#!/bin/bash
# Debug one carrier page: start serve.py, run headless Chrome with console logging, print stderr tail + pre content.
# Usage: dbg-measure.sh <harness> <mockdir> <port> [query]
set -u
ROOT="E:/workspaces/hioas/hioas-aap-001"
CHROME="/c/Program Files/Google/Chrome/Application/chrome.exe"
TMP="$LOCALAPPDATA/Temp"
H=$1; M=$2; P=$3; Q="${4:-}"
DST="$ROOT/aap-client/dist/build/h5"
cp "$ROOT/.agents/state/h5-measure/$H" "$DST/"
python "$ROOT/.agents/state/h5-measure/serve.py" "$DST" "$ROOT/$M" "$P" > "$TMP/dbg-serve.log" 2>&1 &
S=$!
sleep 2
"$CHROME" --headless=new --disable-gpu --no-sandbox --hide-scrollbars \
  --virtual-time-budget=30000 --user-data-dir="$TMP/chrome-dbg" \
  --enable-logging=stderr --v=0 \
  --dump-dom "http://127.0.0.1:$P/$H$Q" > "$TMP/dbg-dom.html" 2> "$TMP/dbg-chrome.log"
kill $S 2>/dev/null
echo "--- console/log lines mentioning ERR/CONSOLE/Uncaught:"
grep -iE "uncaught|error|CONSOLE" "$TMP/dbg-chrome.log" | head -20
echo "--- pre content:"
python "$ROOT/.agents/state/extract-inline-js.py" /dev/null /dev/null 2>/dev/null
grep -o 'id="m">[^<]\{0,400\}' "$TMP/dbg-dom.html" | head -3
