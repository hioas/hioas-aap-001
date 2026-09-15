#!/bin/bash
# 序号 12 测量：dump-dom（phase1/2/3）→ evidence/measure-序号12-<tag>.json
# ⚠️ 给原生工具（python/chrome）必须传 Windows 路径（MSYS 路径不会被转换）
set -e
ROOT="E:/workspaces/hioas/hioas-aap-001"
CHROME="/c/Program Files/Google/Chrome/Application/chrome.exe"
TMP="$LOCALAPPDATA/Temp"
TAG=$1
PORT=5219

"$CHROME" --headless=new --disable-gpu --no-sandbox --hide-scrollbars \
  --virtual-time-budget=25000 --user-data-dir="$TMP/chrome-m12-$TAG" \
  --dump-dom "http://127.0.0.1:$PORT/__measure-quote-preview.html" > "$TMP/m12-$TAG.html" 2>/dev/null

echo "dump bytes: $(wc -c < "$TMP/m12-$TAG.html")"
python "$ROOT/.agents/state/extract-measure-json.py" "$TMP/m12-$TAG.html" "$ROOT/aap-client/evidence/measure-序号12-$TAG.json"
echo "json bytes: $(wc -c < "$ROOT/aap-client/evidence/measure-序号12-$TAG.json")"
