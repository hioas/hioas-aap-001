#!/bin/bash
# 复核用：对某个 __measure-*.html 载体页跑 430 宽 DOM 实测两遍（run1/run2）并证明一致。
# 用法: review-measure.sh <序号tag> <载体页文件名> <mock目录> <端口>
#   例: review-measure.sh 3 __measure.html .agents/state/h5-measure/api 5301
# 证据: .agents/state/evidence/review-序号<tag>-run{1,2}.json
set -u
ROOT="E:/workspaces/hioas/hioas-aap-001"
CHROME="/c/Program Files/Google/Chrome/Application/chrome.exe"
TMP="$LOCALAPPDATA/Temp"
TAG=$1; HARNESS=$2; MOCK=$3; PORT=$4
DST="$ROOT/aap-client/dist/build/h5"

cp "$ROOT/.agents/state/h5-measure/$HARNESS" "$DST/" || { echo "载体页拷贝失败 $HARNESS"; exit 1; }

python "$ROOT/.agents/state/h5-measure/serve.py" "$DST" "$ROOT/$MOCK" "$PORT" > "$TMP/serve-review-$TAG.log" 2>&1 &
SRV=$!
sleep 2

for RUN in 1 2; do
  "$CHROME" --headless=new --disable-gpu --no-sandbox --hide-scrollbars \
    --virtual-time-budget=25000 --user-data-dir="$TMP/chrome-review-$TAG-$RUN" \
    --dump-dom "http://127.0.0.1:$PORT/$HARNESS" > "$TMP/rev-$TAG-$RUN.html" 2>/dev/null
  echo "run$RUN dump bytes: $(wc -c < "$TMP/rev-$TAG-$RUN.html")"
  python "$ROOT/.agents/state/extract-measure-json.py" "$TMP/rev-$TAG-$RUN.html" \
    "$ROOT/.agents/state/evidence/review-序号$TAG-run$RUN.json"
done

kill $SRV 2>/dev/null
wait $SRV 2>/dev/null
echo "server $PORT stopped"
