#!/bin/bash
# 起静态取证服务器（本循环自用）→ 拍 430 宽截图 → 关掉自己起的服务器
# 用法: shot-430.sh <输出.png> [载体页=__measure.html] [查询串=?shot=1]
set -u
ROOT="E:/workspaces/hioas/hioas-aap-001"
CHROME="/c/Program Files/Google/Chrome/Application/chrome.exe"
TMP="$LOCALAPPDATA/Temp"
PORT=5343
OUT="$1"
HARNESS="${2:-__measure.html}"
QUERY="${3:-?shot=1}"
LOG="$TMP/serve-shot-$PORT.log"

cp "$ROOT/.agents/state/h5-measure/$HARNESS" "$ROOT/aap-client/dist/build/h5/" || { echo "载体页拷贝失败 $HARNESS"; exit 1; }

: > "$LOG"
python "$ROOT/.agents/state/h5-measure/serve.py" "$ROOT/aap-client/dist/build/h5" "$ROOT/.agents/state/h5-measure/api" "$PORT" > "$LOG" 2>&1 &
SRV=$!
sleep 3
echo "harness http=$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$PORT/$HARNESS$QUERY")"
"$CHROME" --headless=new --disable-gpu --no-sandbox --hide-scrollbars --window-size=440,1000 \
  --virtual-time-budget=25000 --user-data-dir="$TMP/chrome-shot-$PORT" \
  --screenshot="$OUT" "http://127.0.0.1:$PORT/$HARNESS$QUERY" 2>/dev/null
kill $SRV 2>/dev/null
wait $SRV 2>/dev/null
echo "server $PORT stopped"
ls -la "$OUT"
