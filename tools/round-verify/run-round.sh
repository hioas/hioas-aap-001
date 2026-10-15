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
# 窗口起止三值必须**同源**（单次时钟读取后派生）：写成多次独立 `date` 调用时，两次调用之间跨过一个秒界
# 会让 `FACTS_WINDOW_START`（HH:MM:SS）早于 `FACTS_WINDOW_START_ISO` 一秒 ⇒ facts **自相矛盾**，
# 消费方（windowtime.resolve_window_seq → analyze A5 / independent J1g）会把合法的 HH:MM:SS 判成
# 「窗口内合法落位 0 个」而报失败。该竞态是真实触发过的（概率约 10ms/1s 每次跑测），故改为单次读取。
WS=$(date +%s)
log "FACTS_WINDOW_START=$(date -d "@$WS" +%H:%M:%S)"
log "FACTS_WINDOW_START_TS=$WS"
log "FACTS_WINDOW_START_ISO=$(date -d "@$WS" '+%Y-%m-%d %H:%M:%S')"
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

# ---- worktree 回收（三层：先离开该树 → 有界重试 → 残留兜底）----
# 真实返工（巡检轮实测：同一 HEAD 连续两次逐轮复现）：Windows **不允许删除任何进程的当前目录（含其祖先）**，
# 而上面 `cd "$WT/aap-server"` 之后 bash 的 CWD 就在树内 ⇒ `git worktree remove --force` 以
# `error: failed to delete '<WT>': Permission denied`（rc=255）**半途失败**：目录残留部分文件、
# 而 worktree 登记项已被摘除 ⇒ `analyze.py` A20、`independent.py` J1e/J5g 响亮 FAIL、整轮证据不可用。
# 最小复现（本机实测）：worktree 子目录内 `cd` 后 `git -C <主库> worktree remove --force <wt>` ⇒ rc=255 + 残留；
# 从树外执行 ⇒ rc=0 + 目录消失。故此处先 `cd` 出树，再重试，最后交 `rm-tree.py` 兜底。
cd "$ROOT" 2>/dev/null || cd "$W" 2>/dev/null || true
git -C "$ROOT" worktree remove --force "$WT" >>"$W/wt.log" 2>&1
RM_GIT_RC=$?
RM_RETRIES=0
while [ "$RM_GIT_RC" != "0" ] && [ "$RM_RETRIES" -lt 2 ]; do
  RM_RETRIES=$((RM_RETRIES + 1))
  sleep 5
  git -C "$ROOT" worktree prune >>"$W/wt.log" 2>&1
  git -C "$ROOT" worktree remove --force "$WT" >>"$W/wt.log" 2>&1
  RM_GIT_RC=$?
done
log "WORKTREE_REMOVE_GIT_RC=$RM_GIT_RC"
log "WORKTREE_REMOVE_RETRIES=$RM_RETRIES"
RM_RESID=0
if [ -d "$WT" ]; then
  RMPY="$(type -p python)"
  if [ -n "${RMPY:-}" ]; then
    "$RMPY" "$ROOT/tools/round-verify/rm-tree.py" "$WT" >>"$W/wt.log" 2>&1
    RM_RESID=$?
  else
    RM_RESID=127
  fi
fi
log "WORKTREE_REMOVE_RESIDUE_PY_RC=$RM_RESID"
git -C "$ROOT" worktree prune >>"$W/wt.log" 2>&1
# WORKTREE_REMOVE_RC 的语义 = 「**已回收**」（磁盘不存在 ∧ git 未登记）—— 三层里任一层成功即为 0，
# 且把 git 首层 rc / 重试次数 / 兜底 rc 全部单独留痕（不掩盖中间失败，历史 12/175）。
if [ ! -d "$WT" ] && ! git -C "$ROOT" worktree list --porcelain 2>/dev/null | grep -qF "$WT"; then
  log "WORKTREE_REMOVE_RC=0"
else
  log "WORKTREE_REMOVE_RC=1"
fi
# 窗口尾三值同上：**同源派生**（理由见窗口起点处的注释）。
WE=$(date +%s)
log "FACTS_WINDOW_END=$(date -d "@$WE" +%H:%M:%S)"
log "FACTS_WINDOW_END_TS=$WE"
log "FACTS_WINDOW_END_ISO=$(date -d "@$WE" '+%Y-%m-%d %H:%M:%S')"
log "FACTS_HEAD_AT_END=$(git -C "$ROOT" rev-parse --short HEAD)"
H1=$(git -C "$ROOT" rev-parse HEAD)
log "FACTS_HEAD_AT_END_FULL=$H1"
ADV=$(git -C "$ROOT" rev-list --count "$H0..$H1")
log "FACTS_HEAD_ADVANCED_COUNT=$ADV"
log "FACTS_WRITTEN=1"
echo "EXECUTOR_DONE=$W"
