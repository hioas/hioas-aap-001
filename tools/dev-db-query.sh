#!/usr/bin/env bash
# 查 aap_server_dev 的账号与角色（凭据从 /mnt/e/env/aap-server.env 注入，不落盘、不回显）
set -a; . /mnt/e/env/aap-server.env; set +a
SQL="${1:-select id, phone_mask, role, status from aap_provider_account order by id limit 30;}"
docker exec -e PGPASSWORD="$DB_PASSWORD" dev_postgres \
  psql -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1 -c "$SQL"
