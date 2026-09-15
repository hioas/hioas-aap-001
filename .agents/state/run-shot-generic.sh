#!/bin/bash
# 通用整页截图：<carrier 文件名> <输出名> <高度> <端口> [query]
# 1) 用 430 宽 iframe 载体页截图（headless 的 --window-size 不可靠 → 靠 png-crop 裁到 iframe 矩形）
# 2) 先写 ASCII 临时路径再用 mv 改成中文名（chrome 对中文 --screenshot 参数会静默不落盘，SKILL §4.9）
set -e
ROOT="E:/workspaces/hioas/hioas-aap-001"
CHROME="/c/Program Files/Google/Chrome/Application/chrome.exe"
TMP="$LOCALAPPDATA/Temp"
OUT="$ROOT/logs/screenshots"
CARRIER=$1
NAME=$2
H=$3
PORT=$4
QUERY=${5:-noaction=1}

"$CHROME" --headless=new --disable-gpu --no-sandbox --hide-scrollbars --virtual-time-budget=20000 \
  --user-data-dir="$TMP/chrome-shot-$PORT-$H" --window-size=430,"$H" \
  --screenshot="$TMP/shot-raw-$PORT.png" "http://127.0.0.1:$PORT/$CARRIER?$QUERY" 2>/dev/null

ls -la "$TMP/shot-raw-$PORT.png"
python "$ROOT/.agents/state/png-crop.py" "$TMP/shot-raw-$PORT.png" "$TMP/shot-crop-$PORT.png" "0,0,430,$H"
mv "$TMP/shot-crop-$PORT.png" "$OUT/$NAME.png"
python "$ROOT/.agents/state/png-size.py" "$OUT/$NAME.png"
