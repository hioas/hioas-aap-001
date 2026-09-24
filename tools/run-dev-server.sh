#!/usr/bin/env bash
# 本地 dev 后端启动器（闭环验收用）。
#
# 为什么单独一个脚本：闭环链路的最后两段需要在 dev profile 下开三个开关，缺一即断：
#   * AAP_ALLOW_LOOPBACK=true   —— 上架同步要出站到本地桩（127.0.0.1:9911），
#                                  否则 SSRF 守卫直接拒；默认 false 是生产安全口径，不能改默认值。
#   * AAP_SMS_EXPOSE_CODE=true  —— 联调要拿 dev_code 登录（无真实短信通道）。
#   * AAP_USAGE_LOG_FILE=<path> —— 用量归集的日志源（无 new-api Log 表可读时的 mock 适配器）。
#
# 用法：
#   bash tools/run-dev-server.sh                  # 用默认端口（来自 E:/env/aap-server.env）
#   AAP_USAGE_LOG_FILE=/c/temp/x.json bash tools/run-dev-server.sh
#
# 依赖：E:/env/aap-server.env（数据库/密钥等），由 tools/with-env.sh 注入。
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
: "${AAP_USAGE_LOG_FILE:=${LOCALAPPDATA:-/tmp}/Temp/biz-closure-usage-log.json}"

cd "$ROOT/aap-server"
exec ../tools/with-env.sh aap-server bash -c \
  "export AAP_ALLOW_LOOPBACK=true AAP_SMS_EXPOSE_CODE=true AAP_USAGE_LOG_FILE='${AAP_USAGE_LOG_FILE}'; exec mvn -o -B -ntp spring-boot:run"
