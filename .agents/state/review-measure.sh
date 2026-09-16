#!/bin/bash
# 复核用：对某个 __measure-*.html 载体页跑 430 宽 DOM 实测两遍（run1/run2）并证明一致。
# 用法: review-measure.sh <序号tag> <载体页文件名> <mock目录> <端口> [url查询串]
#   例: review-measure.sh 3 __measure.html .agents/state/h5-measure/api 5301
#       review-measure.sh 1-guard __measure-login.html .agents/state/h5-measure/api 5312 "?scenario=guard"
# 证据: .agents/state/evidence/review-序号<tag>-run{1,2}.json
#       .agents/state/evidence/requests-序号<tag>-run{1,2}.txt（该轮 serve 实际收到的请求行；写请求带 body）
set -u
ROOT="E:/workspaces/hioas/hioas-aap-001"
CHROME="/c/Program Files/Google/Chrome/Application/chrome.exe"
TMP="$LOCALAPPDATA/Temp"
TAG=$1; HARNESS=$2; MOCK=$3; PORT=$4; QUERY="${5:-}"
DST="$ROOT/aap-client/dist/build/h5"
EVD="$ROOT/.agents/state/evidence"

cp "$ROOT/.agents/state/h5-measure/$HARNESS" "$DST/" || { echo "载体页拷贝失败 $HARNESS"; exit 1; }

LOG="$TMP/serve-review-$TAG.log"
: > "$LOG"
python "$ROOT/.agents/state/h5-measure/serve.py" "$DST" "$ROOT/$MOCK" "$PORT" > "$LOG" 2>&1 &
SRV=$!
sleep 2

for RUN in 1 2; do
  BEFORE=$(wc -c < "$LOG")
  "$CHROME" --headless=new --disable-gpu --no-sandbox --hide-scrollbars \
    --virtual-time-budget=25000 --user-data-dir="$TMP/chrome-review-$TAG-$RUN" \
    --dump-dom "http://127.0.0.1:$PORT/$HARNESS$QUERY" > "$TMP/rev-$TAG-$RUN.html" 2>/dev/null
  echo "run$RUN dump bytes: $(wc -c < "$TMP/rev-$TAG-$RUN.html")"
  python "$ROOT/.agents/state/extract-measure-json.py" "$TMP/rev-$TAG-$RUN.html" \
    "$EVD/review-序号$TAG-run$RUN.json"
  tail -c "+$((BEFORE + 1))" "$LOG" \
    | grep -E '\[serve\] ("?(GET|POST|PUT|DELETE).*/api/)' \
    | sed 's/^\[serve\] //' > "$EVD/requests-序号$TAG-run$RUN.txt"
  echo "requests run$RUN: $(wc -l < "$EVD/requests-序号$TAG-run$RUN.txt") 行"
done

kill $SRV 2>/dev/null
wait $SRV 2>/dev/null
echo "server $PORT stopped"
