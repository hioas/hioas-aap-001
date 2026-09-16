#!/bin/bash
# 序号 21（【工作台与我的】我的 2，整页 990 = 设计帧高）430 宽整页截图：
# ASCII 临时名 → cp 成中文名（Chrome --screenshot 收到含中文的 MSYS 相对路径会静默失败 —— 状态文件 §5 记过）
# 载体页 ?shot=1 时 iframe 高 = 设计帧高 990（TabBar fixed 在 906..990，与设计帧一致）
# 用法: bash .agents/state/shot-21.sh [输出文件名]
set -u
ROOT="E:/workspaces/hioas/hioas-aap-001"
CHROME="/c/Program Files/Google/Chrome/Application/chrome.exe"
TMP="$LOCALAPPDATA/Temp"
PORT=5373
NAME="${1:-20260916-序21-我的页-checks轮-h5-430宽.png}"
HARNESS="__measure-mine.html"
MOCK="api-21"
LOG="$TMP/serve-shot21.log"

cp "$ROOT/.agents/state/h5-measure/$HARNESS" "$ROOT/aap-client/dist/build/h5/" || { echo "载体页拷贝失败"; exit 1; }
: > "$LOG"
python "$ROOT/.agents/state/h5-measure/serve.py" "$ROOT/aap-client/dist/build/h5" "$ROOT/.agents/state/h5-measure/$MOCK" "$PORT" > "$LOG" 2>&1 &
SRV=$!
sleep 3
echo "harness http=$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$PORT/$HARNESS?shot=1")"
"$CHROME" --headless=new --disable-gpu --no-sandbox --hide-scrollbars \
  --window-size=430,990 --virtual-time-budget=25000 --user-data-dir="$TMP/chrome-shot21" \
  --screenshot="$TMP/shot21.png" "http://127.0.0.1:$PORT/$HARNESS?shot=1" 2>/dev/null
kill $SRV 2>/dev/null
wait $SRV 2>/dev/null
echo "server $PORT stopped"
if [ -f "$TMP/shot21.png" ]; then
  mkdir -p "$ROOT/logs/screenshots"
  cp "$TMP/shot21.png" "$ROOT/logs/screenshots/$NAME"
  cp "$TMP/shot21.png" "$ROOT/.agents/state/evidence/$NAME"
  python "$ROOT/.agents/state/png-size.py" "$ROOT/.agents/state/evidence/$NAME"
else
  echo "截图未生成"
fi
