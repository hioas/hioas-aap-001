#!/bin/bash
# 序号 8（报价单列表，整页 1206）430 宽整页截图：ASCII 临时名 → cp 成中文名
# （Chrome --screenshot 收到含中文的 MSYS 相对路径会静默失败 —— 状态文件 §5 记过）
# 用法: bash .agents/state/shot-8.sh [输出文件名]
set -u
ROOT="E:/workspaces/hioas/hioas-aap-001"
CHROME="/c/Program Files/Google/Chrome/Application/chrome.exe"
TMP="$LOCALAPPDATA/Temp"
PORT=5345
NAME="${1:-20260916-序08-报价单列表-checks轮-h5-430宽.png}"
HARNESS="__measure-quotes.html"
LOG="$TMP/serve-shot8.log"

cp "$ROOT/.agents/state/h5-measure/$HARNESS" "$ROOT/aap-client/dist/build/h5/" || { echo "载体页拷贝失败"; exit 1; }
: > "$LOG"
python "$ROOT/.agents/state/h5-measure/serve.py" "$ROOT/aap-client/dist/build/h5" "$ROOT/.agents/state/h5-measure/api" "$PORT" > "$LOG" 2>&1 &
SRV=$!
sleep 3
echo "harness http=$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$PORT/$HARNESS")"
"$CHROME" --headless=new --disable-gpu --no-sandbox --hide-scrollbars \
  --window-size=430,1206 --virtual-time-budget=25000 --user-data-dir="$TMP/chrome-shot8" \
  --screenshot="$TMP/shot8.png" "http://127.0.0.1:$PORT/$HARNESS?shot=1" 2>/dev/null
kill $SRV 2>/dev/null
wait $SRV 2>/dev/null
echo "server $PORT stopped"
if [ -f "$TMP/shot8.png" ]; then
  mkdir -p "$ROOT/logs/screenshots"
  cp "$TMP/shot8.png" "$ROOT/logs/screenshots/$NAME"
  cp "$TMP/shot8.png" "$ROOT/.agents/state/evidence/$NAME"
  ls -la "$ROOT/logs/screenshots/$NAME" "$ROOT/.agents/state/evidence/$NAME"
else
  echo "截图未生成"
fi
