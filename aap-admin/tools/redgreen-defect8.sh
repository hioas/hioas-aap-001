#!/usr/bin/env bash
# 先红后绿：缺陷8（分页参数名 page_size → 后端静默忽略）的回归判据实测
# 判据：tests/unit/providers.spec.ts「分页参数名是 pageSize（不是 page_size）」
# 红：把 providers.ts 的查询键改回 page_size（= 复原缺陷）→ 该用例必须响亮失败
# 绿：恢复 pageSize → 全绿
set -u
cd "$(dirname "$0")/.." || exit 1
F=src/api/admin/providers.ts
OUT=../.agents/state/evidence/redgreen-defect8-vitest.txt

{
  echo "### 缺陷8 回归判据的先红后绿（真实 vitest 输出，非手写）"
  echo "### 判据：aap-admin/tests/unit/providers.spec.ts > 分页参数名是 pageSize（不是 page_size）"
  echo
  echo "===== RED：$F 查询键改回 page_size（复原缺陷8）====="
} > "$OUT"

python - <<'PY'
import io
p = 'src/api/admin/providers.ts'
s = io.open(p, encoding='utf-8').read()
s2 = s.replace('        pageSize: params.pageSize ?? 20,', '        page_size: params.pageSize ?? 20,')
assert s2 != s, 'RED 注入失败：未找到 pageSize 查询键'
io.open(p, 'w', encoding='utf-8', newline='\n').write(s2)
PY

npx vitest run tests/unit/providers.spec.ts >> "$OUT" 2>&1
echo "RED exit=$?" >> "$OUT"

{
  echo
  echo "===== GREEN：恢复 pageSize ====="
} >> "$OUT"

python - <<'PY'
import io
p = 'src/api/admin/providers.ts'
s = io.open(p, encoding='utf-8').read()
s2 = s.replace('        page_size: params.pageSize ?? 20,', '        pageSize: params.pageSize ?? 20,')
assert s2 != s, 'GREEN 恢复失败'
io.open(p, 'w', encoding='utf-8', newline='\n').write(s2)
PY

npx vitest run tests/unit/providers.spec.ts >> "$OUT" 2>&1
echo "GREEN exit=$?" >> "$OUT"

# 证据文件统一 LF
python - <<'PY'
import io
p = '../.agents/state/evidence/redgreen-defect8-vitest.txt'
s = io.open(p, encoding='utf-8', newline='').read().replace('\r\n', '\n')
io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
p2 = '../.agents/state/evidence/redgreen-defect8-pageSize.txt'
s2 = io.open(p2, encoding='utf-8', newline='').read().replace('\r\n', '\n')
io.open(p2, 'w', encoding='utf-8', newline='\n').write(s2)
PY

grep -nE "Tests |RED exit|GREEN exit|AssertionError" "$OUT" | head -20
echo "CR 残留检查: $(python -c "import io;s=io.open('../.agents/state/evidence/redgreen-defect8-vitest.txt','rb').read();print(s.count(b'\r'))")"
