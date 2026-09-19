#!/usr/bin/env bash
# 抓管理端 11 页的 design / interaction / screenshot（逐页，不一次性拉全画布）
set -u
export PATH="$HOME/.calicat-cli/bin:$PATH"
cd E:/workspaces/hioas/hioas-aap-001
SK="C:/Users/laitz/AppData/Local/hermes/skills/calicat"
URL="https://www.calicat.cn/design/2100748148891054080"

python - <<'PY' > /tmp/admin-pages.tsv
import json, io
d = json.load(io.open('.calicat-admin/inventory.json', encoding='utf-8'))
for p in d['pages']:
    print(f"{p['id']}\t{p['sourceLayerId']}\t{p['name']}")
PY

while IFS=$'\t' read -r pid lid name; do
  [ -z "$pid" ] && continue
  echo "=== $pid  $name ==="
  python "$SK/scripts/calicat_source.py" page --url "$URL" --layer-id "$lid" --page-id "$pid" --out .calicat-admin 2>&1 | tail -2
done < /tmp/admin-pages.tsv

echo
echo "=== 抓取结果 ==="
python - <<'PY'
import json, io, os
d = json.load(io.open('.calicat-admin/inventory.json', encoding='utf-8'))
for p in d['pages']:
    d1 = os.path.join('.calicat-admin', 'raw', 'pages', p['id'])
    files = sorted(os.listdir(d1)) if os.path.isdir(d1) else []
    sizes = {f: os.path.getsize(os.path.join(d1, f)) for f in files}
    print(f"{p['id']:16s} design={p.get('designCaptured')} inter={p.get('interactionCaptured')}  {sizes}")
PY
