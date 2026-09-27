#!/bin/bash
# 全量测试两轮串行执行器（**轮次无关**：轮次号由参数给出，不再逐轮机械派生 —— 历史 201/206/243-③ 的结构性消除）。
#
# 用法：bash tools/round-verify/run-round.sh R490
# 行为：① 并发前置（正/反双向对照）② 在 HEAD 的**独立 worktree**（带时间戳唯一名，cron 下禁止先删再建）内
#       串行跑两轮全量 ③ 归档 coverage-report.json + 测试源码 ④ 回收 worktree ⑤ 把全部纯值落盘为 facts。
# 纪律：facts 是纯值的**单一事实源**（窗口起止 / HEAD / 被测提交 / rc / 轮次），消费方只读（历史 243-③）；
#       环境指纹由本 bash 落盘（历史 240/251：跨语言判可达性会得出相反结论）；
#       绝不按镜像名杀进程、绝不触碰他方 worktree / 浏览器（多项目共存硬规则）。
set -uo pipefail
export PATH="$HOME/bin:$PATH"

ROUND="${1:?用法: bash tools/round-verify/run-round.sh R490}"
case "$ROUND" in
  R[0-9]*) : ;;
  *) echo "ABORT_BAD_ROUND=$ROUND"; exit 4 ;;
esac

ROOT="E:/workspaces/hioas/hioas-aap-001"
T="C:/Users/laitz/AppData/Local/Temp"
W="$T/aap-round-verify/$ROUND"
STAMP=$(date +%H%M%S)
WT="$T/aap-round-wt-$ROUND-$STAMP"
FACTS="$W/facts-$ROUND.log"
mkdir -p "$W" || exit 3
: > "$FACTS"
log() { echo "$*" | tee -a "$FACTS"; }

LOCK="$W/.round.pid"
if [ -e "$LOCK" ]; then
  OLDPID=$(cat "$LOCK" 2>/dev/null || true)
  if [ -n "${OLDPID:-}" ] && kill -0 "$OLDPID" 2>/dev/null; then
    echo "ABORT_LOCK_EXISTS=$OLDPID"; exit 8
  fi
  log "STALE_LOCK_FROM=$OLDPID"
fi
echo $$ > "$LOCK"
trap 'rm -f "$LOCK"' EXIT

log "ENV_BASH=$(type -p bash)"
log "ENV_UNAME=$(uname -s)"
log "ENV_MVN=$(type -p mvn)"
log "ENV_JAVA=$(type -p java)"
JPS="$(dirname "$(type -p java 2>/dev/null)")/jps"
log "ENV_JPS=$JPS"
if [ -x "$JPS" ]; then log "ENV_JPS_REACHABLE=Y"; else log "ENV_JPS_REACHABLE=N"; fi
log "FACTS_ROUND=$ROUND"
log "FACTS_WINDOW_START=$(date +%H:%M:%S)"
log "FACTS_WINDOW_START_TS=$(date +%s)"
log "FACTS_WINDOW_START_ISO=$(date '+%Y-%m-%d %H:%M:%S')"
log "FACTS_HEAD_AT_START=$(git -C "$ROOT" rev-parse --short HEAD)"
H0=$(git -C "$ROOT" rev-parse HEAD)
log "FACTS_HEAD_AT_START_FULL=$H0"

is_test_line() {
  echo "$1" | grep -qE 'surefirebooter|surefire' && return 0
  if echo "$1" | grep -q 'classworlds.launcher.Launcher'; then
    echo "$1" | grep -qE '(^|[[:space:]])(test|verify)([[:space:]]|$)' && return 0
  fi
  return 1
}

CP=0; CN=0
for l in \
  '111 a.b.c surefire com.example.surefirebooter-1234.jar' \
  '222 org.codehaus.plexus.classworlds.launcher.Launcher -B -ntp test' ; do
  is_test_line "$l" && CP=$((CP+1))
done
for l in \
  '333 org.codehaus.plexus.classworlds.launcher.Launcher -o -B -ntp spring-boot:run' \
  '444 org.jetbrains.idea.maven.server.RemoteMavenServer36' ; do
  is_test_line "$l" && CN=$((CN+1))
done
log "PREFLIGHT_CONTROL_POS_MATCH=$CP/2"
log "PREFLIGHT_CONTROL_NEG_MATCH=$CN/2（必须 0）"
[ "$CP" = "2" ] && [ "$CN" = "0" ] || { log "PREFLIGHT_RESULT=CONTROL_FAILED_ABORT"; exit 7; }

busy_probe() {
  SNAP="$("$JPS" -l -m 2>/dev/null)"
  echo "$SNAP" | grep -E 'classworlds|surefire' | while read -r ln; do
    is_test_line "$ln" && echo "PREFLIGHT_BUSY_TESTJVM=$(echo "$ln" | cut -c1-160)" >> "$FACTS"
  done
  echo "$SNAP" | grep -E 'classworlds|surefire' | while read -r ln; do
    is_test_line "$ln" && echo BUSY
  done | wc -l | tr -d ' '
}
CONC=""
for i in 1 2 3 4 5 6; do
  H=$(busy_probe | tail -1)
  log "PREFLIGHT_TICK=$i BUSY_TEST_JVM=$H"
  if [ "$H" = "0" ]; then CONC=0; break; fi
  sleep 10
done
[ "${CONC:-}" = "0" ] || { log "PREFLIGHT_RESULT=CONC_BUSY_ABORT"; exit 9; }
log "PREFLIGHT_RESULT=CLEAR"
log "PREFLIGHT_OK=1"

git -C "$ROOT" status --porcelain > "$W/root-status-before.txt" 2>&1
log "ROOT_STATUS_LINES_BEFORE=$(grep -c . "$W/root-status-before.txt")"

git -C "$ROOT" worktree add --detach "$WT" HEAD >>"$W/wt.log" 2>&1
WTRC=$?
log "WORKTREE_ADD_RC=$WTRC"
log "WORKTREE_PATH=$WT"
[ "$WTRC" = "0" ] || { log "ABORT_WORKTREE"; exit 10; }
log "FACTS_TESTED_COMMIT=$(git -C "$WT" rev-parse --short HEAD)"
log "FACTS_TESTED_COMMIT_FULL=$(git -C "$WT" rev-parse HEAD)"
log "FACTS_TESTED_SUBJECT=$(git -C "$WT" log -1 --format=%s)"
git -C "$WT" diff --stat HEAD -- aap-server/ > "$W/wt-vs-head.txt" 2>&1
log "WT_DIRTY_LINES=$(grep -c . "$W/wt-vs-head.txt")"

ARGS=(mvn -B -ntp test)
cd "$WT/aap-server" || { log "ABORT_NO_MODULE"; exit 11; }
for R in 1 2; do
  S=$(date +%H:%M:%S)
  ../tools/with-env.sh aap-server "${ARGS[@]}" > "$W/run$R.raw" 2>&1
  RC=$?
  E=$(date +%H:%M:%S)
  log "FACTS_RUN${R}_START=$S"
  log "FACTS_RUN${R}_END=$E"
  log "FACTS_RUN${R}_RC=$RC"
done

ARCH="$W/wt-arch"
mkdir -p "$ARCH/testsrc"
cp -p "$WT/.agents/state/evidence/coverage-report.json" "$ARCH/coverage-report.json" 2>>"$W/wt.log"; log "ARCH_REPORT_RC=$?"
cp -rp "$WT/aap-server/src/test/java/." "$ARCH/testsrc/" 2>>"$W/wt.log"; log "ARCH_TESTSRC_RC=$?"
log "ARCH_TEST_FILES=$(find "$ARCH/testsrc" -name '*.java' 2>/dev/null | wc -l | tr -d ' ')"

git -C "$ROOT" status --porcelain > "$W/root-status-after.txt" 2>&1

git -C "$ROOT" worktree remove --force "$WT" >>"$W/wt.log" 2>&1
log "WORKTREE_REMOVE_RC=$?"
log "FACTS_WINDOW_END=$(date +%H:%M:%S)"
log "FACTS_WINDOW_END_TS=$(date +%s)"
log "FACTS_WINDOW_END_ISO=$(date '+%Y-%m-%d %H:%M:%S')"
log "FACTS_HEAD_AT_END=$(git -C "$ROOT" rev-parse --short HEAD)"
H1=$(git -C "$ROOT" rev-parse HEAD)
log "FACTS_HEAD_AT_END_FULL=$H1"
ADV=$(git -C "$ROOT" rev-list --count "$H0..$H1")
log "FACTS_HEAD_ADVANCED_COUNT=$ADV"
log "FACTS_WRITTEN=1"
echo "EXECUTOR_DONE=$W"
