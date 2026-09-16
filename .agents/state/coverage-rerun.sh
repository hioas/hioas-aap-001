#!/bin/bash
# 队列 1 逐页复核（当前修订版全量版）：22 个载体页各跑两轮 430 宽 DOM 实测。
# 用法: bash .agents/state/coverage-rerun.sh [起点序号]
# 证据: .agents/state/evidence/review-序号cov-<tag>-run{1,2}.json（不覆盖各页 checks 轮留证）
set -u
ROOT="E:/workspaces/hioas/hioas-aap-001"
cd "$ROOT" || exit 1
PORT=5401
START="${1:-}"
SKIP=1
[ -z "$START" ] && SKIP=0

# tag|载体页|mock 目录
MANIFEST="
1|__measure-login.html|.agents/state/h5-measure/api
2|__measure-workbench.html|.agents/state/h5-measure/api
3|__measure.html|.agents/state/h5-measure/api
4|__measure-submit.html|.agents/state/h5-measure/api
4-v1|__measure-form.html|.agents/state/h5-measure/api
5|__measure-detecting.html|.agents/state/h5-measure/api
6|__measure-report.html|.agents/state/h5-measure/api
7|__measure-report-failed.html|.agents/state/h5-measure/api
8|__measure-quotes.html|.agents/state/h5-measure/api
9|__measure-quote-setup.html|.agents/state/h5-measure/api
10|__measure-profile-edit.html|.agents/state/h5-measure/api-10-2
10.1|__measure-profile.html|.agents/state/h5-measure/api-10-1-2
11|__measure-model-pricing.html|.agents/state/h5-measure/api-11
12|__measure-quote-preview.html|.agents/state/h5-measure/api-12
12-v1|__measure-quote-form.html|.agents/state/h5-measure/api-12-v1
12-v2|__measure-quote-apikey.html|.agents/state/h5-measure/api-12-v2
12-v3|__measure-quote-success.html|.agents/state/h5-measure/api-12-v3
15|__measure-contract.html|.agents/state/h5-measure/api-15
20|__measure-messages.html|.agents/state/h5-measure/api-20
21|__measure-mine.html|.agents/state/h5-measure/api-21
22|__measure-usage.html|.agents/state/h5-measure/api-22
23|__measure-settings.html|.agents/state/h5-measure/api-23
"

echo "=== 构建 H5（载体页会被 build 清掉，故 build 后再逐页拷贝） ==="
( cd aap-client && npm run build:h5 ) > "$LOCALAPPDATA/Temp/cov-build.log" 2>&1
echo "build exit=$? ; $(tail -2 "$LOCALAPPDATA/Temp/cov-build.log" | tr '\n' ' ')"

echo "=== 相对时间 mock 复位（序号 20 站内信） ==="
python .agents/state/refresh-notification-mock.py --mock api-20 2>&1 | tail -2

echo "$MANIFEST" | while IFS='|' read -r TAG HARNESS MOCK; do
  [ -z "$TAG" ] && continue
  if [ "$SKIP" = "1" ]; then
    [ "$TAG" = "$START" ] && SKIP=0
    [ "$SKIP" = "1" ] && continue
  fi
  echo "----- 序号 $TAG  ($HARNESS / $MOCK / port $PORT) -----"
  # 序号 20 站内信的时间文案是**相对时间**，mock 时间戳是绝对值 → 该页测量前必须紧邻重置一次，
  # 否则轮次间隔一久就漂成「N 分钟前」的假失败（§5.14 的口径）。
  if [ "$TAG" = "20" ]; then
    python .agents/state/refresh-notification-mock.py --mock api-20 2>&1 | tail -1
  fi
  bash .agents/state/review-measure.sh "cov-$TAG" "$HARNESS" "$MOCK" "$PORT" 2>&1 | tail -3
  PORT=$((PORT + 1))
done
echo "=== 全量复跑结束 ==="
