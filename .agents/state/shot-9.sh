#!/bin/bash
# 序号 9（模型报价设置，整页 1211）430 宽整页截图：ASCII 临时名 → cp 成中文名
# （Chrome --screenshot 收到含中文的 MSYS 相对路径会静默失败 —— 状态文件 §5 记过）
# 用法: bash .agents/state/shot-9.sh [输出文件名]
set -u
ROOT="E:/workspaces/hioas/hioas-aap-001"
CHROME="/c/Program Files/Google/Chrome/Application/chrome.exe"
TMP="$LOCALAPPDATA/Temp"
PORT=5346
NAME="${1:-20260916-序09-模型报价设置-checks轮-h5-430宽.png}"
HARNESS="__measure-quote-setup.html"
LOG="$TMP/serve-shot9.log"

cp "$ROOT/.agents/state/h5-measure/$HARNESS" "$ROOT/aap-client/dist/build/h5/" || { echo "载体页拷贝失败"; exit 1; }
: > "$LOG"
python "$ROOT/.agents/state/h5-measure/serve.py" "$ROOT/aap-client/dist/build/h5" "$ROOT/.agents/state/h5-measure/api" "$PORT" > "$LOG" 2>&1 &
SRV=$!
sleep 3
echo "harness http=$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$PORT/$HARNESS")"
"$CHROME" --headless=new --disable-gpu --no-sandbox --hide-scrollbars \
  --window-size=430,1211 --virtual-time-budget=25000 --user-data-dir="$TMP/chrome-shot9" \
  --screenshot="$TMP/shot9.png" "http://127.0.0.1:$PORT/$HARNESS?shot=1" 2>/dev/null
kill $SRV 2>/dev/null
wait $SRV 2>/dev/null
echo "server $PORT stopped"
if [ -f "$TMP/shot9.png" ]; then
  mkdir -p "$ROOT/logs/screenshots"
  cp "$TMP/shot9.png" "$ROOT/logs/screenshots/$NAME"
  cp "$TMP/shot9.png" "$ROOT/.agents/state/evidence/$NAME"
  ls -la "$ROOT/logs/screenshots/$NAME" "$ROOT/.agents/state/evidence/$NAME"
else
  echo "截图未生成"
fi
