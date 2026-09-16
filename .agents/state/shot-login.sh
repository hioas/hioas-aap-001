#!/bin/bash
# 序号 1（登录注册）430×1114 整页截图 —— 窗口高按**设计帧高 1114**（shot-430.sh 固定 1000 装不下）
# 用法: bash .agents/state/shot-login.sh [输出.png] [查询串=?shot=1]
set -u
ROOT="E:/workspaces/hioas/hioas-aap-001"
CHROME="/c/Program Files/Google/Chrome/Application/chrome.exe"
TMP="$LOCALAPPDATA/Temp"
PORT=5463
OUT="${1:-$ROOT/.agents/state/evidence/20260916-序01-登录注册-字重口径-h5-430宽.png}"
QUERY="${2:-?shot=1}"
LOG="$TMP/serve-shot-login.log"
# Chrome --screenshot 收到含中文的 MSYS 路径会静默写不出 → 先写 ASCII 临时名再 cp
ASCII="$TMP/login-shot.png"

cp "$ROOT/.agents/state/h5-measure/__measure-login.html" "$ROOT/aap-client/dist/build/h5/" || exit 1
: > "$LOG"
python "$ROOT/.agents/state/h5-measure/serve.py" "$ROOT/aap-client/dist/build/h5" "$ROOT/.agents/state/h5-measure/api" "$PORT" > "$LOG" 2>&1 &
SRV=$!
sleep 3
"$CHROME" --headless=new --disable-gpu --no-sandbox --hide-scrollbars --window-size=430,1114 \
  --virtual-time-budget=25000 --user-data-dir="$TMP/chrome-shot-login" \
  --screenshot="$ASCII" "http://127.0.0.1:$PORT/__measure-login.html$QUERY" 2>/dev/null
kill $SRV 2>/dev/null
wait $SRV 2>/dev/null
test -f "$ASCII" || { echo "截图未产出"; exit 1; }
cp "$ASCII" "$OUT"
python "$ROOT/.agents/state/png-size.py" "$OUT"
echo "server $PORT stopped"
