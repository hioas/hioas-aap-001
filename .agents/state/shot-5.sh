#!/bin/bash
# 拍序号 5（page-5-2「检测进行中」）的 430 宽整页截图（?shot=1 停在数据态），
# 输出先落 ASCII 临时名再 cp（Chrome 对中文路径静默失败）。
set -u
ROOT="E:/workspaces/hioas/hioas-aap-001"
CHROME="/c/Program Files/Google/Chrome/Application/chrome.exe"
TMP="$LOCALAPPDATA/Temp"
PORT=5346
OUT_ASC="$TMP/shot5.png"
DST_NAME="${1:-20260916-序05-检测进行中-textleaf轮-h5-430宽.png}"

cp "$ROOT/.agents/state/h5-measure/__measure-detecting.html" "$ROOT/aap-client/dist/build/h5/"
python "$ROOT/.agents/state/h5-measure/serve.py" "$ROOT/aap-client/dist/build/h5" "$ROOT/.agents/state/h5-measure/api" "$PORT" > "$TMP/serve-shot5.log" 2>&1 &
SRV=$!
sleep 3
echo "harness http=$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$PORT/__measure-detecting.html?shot=1")"
rm -f "$OUT_ASC"
"$CHROME" --headless=new --disable-gpu --no-sandbox --hide-scrollbars --window-size=440,1000 \
  --virtual-time-budget=25000 --user-data-dir="$TMP/chrome-shot5" \
  --screenshot="$OUT_ASC" "http://127.0.0.1:$PORT/__measure-detecting.html?shot=1" 2>/dev/null
kill $SRV 2>/dev/null
wait $SRV 2>/dev/null
if [ ! -f "$OUT_ASC" ]; then echo "FAIL 截图未产出"; exit 1; fi
mkdir -p "$ROOT/logs/screenshots" "$ROOT/.agents/state/evidence"
cp "$OUT_ASC" "$ROOT/logs/screenshots/$DST_NAME"
cp "$OUT_ASC" "$ROOT/.agents/state/evidence/$DST_NAME"
ls -la "$ROOT/logs/screenshots/$DST_NAME" "$ROOT/.agents/state/evidence/$DST_NAME"
echo "server $PORT stopped"
