#!/bin/bash
# 序号 12 整页截图（noaction 模式，避免交互回放把 iframe 导航走）
# 1) 用 430 宽 iframe 载体页截图（headless 的 --window-size 不可靠，靠 png-crop 裁到 iframe 矩形）
# 2) 先写 ASCII 临时路径再用 mv 改成中文名（chrome 对中文 --screenshot 参数会静默不落盘）
set -e
ROOT="E:/workspaces/hioas/hioas-aap-001"
CHROME="/c/Program Files/Google/Chrome/Application/chrome.exe"
TMP="$LOCALAPPDATA/Temp"
OUT="$ROOT/logs/screenshots"
NAME=$1
H=$2

"$CHROME" --headless=new --disable-gpu --no-sandbox --hide-scrollbars --virtual-time-budget=20000 \
  --user-data-dir="$TMP/chrome-shot12-$NAME" --window-size=430,"$H" \
  --screenshot="$TMP/m12-shot-raw.png" "http://127.0.0.1:5219/__measure-quote-preview.html?noaction=1" 2>/dev/null

ls -la "$TMP/m12-shot-raw.png"
python "$ROOT/.agents/state/png-crop.py" "$TMP/m12-shot-raw.png" "$TMP/m12-shot-crop.png" "0,0,430,$H"
mv "$TMP/m12-shot-crop.png" "$OUT/$NAME.png"
python "$ROOT/.agents/state/png-size.py" "$OUT/$NAME.png"
