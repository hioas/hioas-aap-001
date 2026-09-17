#!/usr/bin/env bash
# 按 SOUL 约定载入 E:\env\<name>.env 后执行命令：
#   tools/with-env.sh aap-server mvn -B -ntp test
# 不打印任何密钥值（只报告载入了哪些变量名）。
set -euo pipefail

name="${1:?用法: tools/with-env.sh <env-name> <command...>}"
shift

ENV_FILE_MSYS="/e/env/${name}.env"
if [ ! -f "$ENV_FILE_MSYS" ]; then
  echo "缺少环境文件：E:\\env\\${name}.env —— 请先补齐（变量名见 aap-server/.env.example）" >&2
  exit 2
fi

set -a
# shellcheck disable=SC1090
. "$ENV_FILE_MSYS"
set +a

names=$(grep -E '^[A-Za-z_][A-Za-z0-9_]*=' "$ENV_FILE_MSYS" | cut -d= -f1 | tr '\n' ' ')
echo "[with-env] 已载入 E:\\env\\${name}.env 变量：${names}" >&2

exec "$@"
