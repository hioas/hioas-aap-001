#!/bin/bash
# 序号 12（【报价管理】报价预览与提交 2，整页 1027 = 设计帧高）430 宽整页截图：ASCII 临时名 → cp 成中文名
# （Chrome --screenshot 收到含中文的 MSYS 相对路径会静默失败 —— 状态文件 §5 记过）
# 载体页 ?shot=1 时 iframe 高 = 设计帧高 1027（底栏在文档流内，静态渲染即可）
# 用法: bash .agents/state/shot-12.sh [输出文件名]
set -u
ROOT="E:/workspaces/hioas/hioas-aap-001"
CHROME="/c/Program Files/Google/Chrome/Application/chrome.exe"
TMP="$LOCALAPPDATA/Temp"
PORT=5356
NAME="${1:-20260916-序12-报价预览与提交-checks轮-h5-430宽.png}"
HARNESS="__measure-quote-preview.html"
MOCK="api-12"
LOG="$TMP/serve-shot12.log"

cp "$ROOT/.agents/state/h5-measure/$HARNESS" "$ROOT/aap-client/dist/build/h5/" || { echo "载体页拷贝失败"; exit 1; }
: > "$LOG"
python "$ROOT/.agents/state/h5-measure/serve.py" "$ROOT/aap-client/dist/build/h5" "$ROOT/.agents/state/h5-measure/$MOCK" "$PORT" > "$LOG" 2>&1 &
SRV=$!
sleep 3
echo "harness http=$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$PORT/$HARNESS?shot=1")"
"$CHROME" --headless=new --disable-gpu --no-sandbox --hide-scrollbars \
  --window-size=430,1027 --virtual-time-budget=25000 --user-data-dir="$TMP/chrome-shot12" \
  --screenshot="$TMP/shot12.png" "http://127.0.0.1:$PORT/$HARNESS?shot=1" 2>/dev/null
kill $SRV 2>/dev/null
wait $SRV 2>/dev/null
echo "server $PORT stopped"
if [ -f "$TMP/shot12.png" ]; then
  mkdir -p "$ROOT/logs/screenshots"
  cp "$TMP/shot12.png" "$ROOT/logs/screenshots/$NAME"
  cp "$TMP/shot12.png" "$ROOT/.agents/state/evidence/$NAME"
  ls -la "$ROOT/logs/screenshots/$NAME" "$ROOT/.agents/state/evidence/$NAME"
else
  echo "截图未生成"
fi
