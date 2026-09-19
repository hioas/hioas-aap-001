#!/usr/bin/env python3
"""证据文件的敏感值守卫：扫描 / 脱敏（共享工具，两端通用）。

背景（真实教训，2026-09-19 夜实测）：
    验收脚本把后端响应体原样写进证据 JSON，其中 `/auth/sms/login` 的响应含
    **真实 access token（303/307 字符 JWT）与 refresh token（43 字符）** ——
    `aap-admin/evidence/admin/admin-acceptance.json` 与
    `aap-client/evidence/h5-chain/h5-chain-result.json` 都命中，
    后者**已经进了 git**。项目硬规则要求「提交前敏感值自检」，但自检若只靠人眼，
    这条就会漏：**工具输出层会把 JWT 打码显示**（`eyJhbG...xxxx`），
    看日志会以为「已经脱敏了」。所以守卫必须是机器判据，且落在**写文件这一步**。

用法：
    python tools/evidence-secrets.py                 # 只扫描，命中即 exit 1（可作门禁）
    python tools/evidence-secrets.py --redact        # 就地脱敏（**纯文本替换**，不动其它字节）
    python tools/evidence-secrets.py --redact --path aap-admin/evidence/admin/admin-acceptance.json

设计取舍（踩过的坑）：
  * **纯文本替换**，不做 json.load + json.dumps 重写 —— 后者会把整份证据重新格式化
    （行尾、缩进、键序全变），对他方会话的证据文件是**无谓 churn**，还会打乱他们
    「产物零写副作用（size+md5）」的回归守卫。第一次实现就是这么干的，已回退。
  * 键名**用白名单精确匹配**，不用子串包含 —— 第一版用 `/token/` 子串匹配，
    把 `tokenPage`（CSS 令牌取值的证据字段）也当成密钥脱敏了，属误伤。
"""
from __future__ import annotations

import argparse
import hashlib
import io
import os
import re
import sys

DEFAULT_ROOTS = ['.agents/state/evidence', 'aap-admin/evidence', 'aap-client/evidence', 'docs', 'evidence']

# 真 JWT：三段、每段至少 8 字符、**不含省略号**（打码后的 eyJhbG...xxx 不匹配）
JWT_RE = re.compile(r'eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}')

# 键名白名单（精确匹配，允许 snake/camel；**不用子串**，避免 tokenPage 这类误伤）
SECRET_KEYS = (
    r'token|access_?token|refresh_?token|id_?token|api_?key|apikey|secret|client_?secret'
    r'|password|passwd|authorization|credentials?'
)
KV_RE = re.compile(r'("(?:' + SECRET_KEYS + r')"\s*:\s*")([^"]{16,})(")', re.I)

SCAN_SUFFIXES = ('.json', '.txt', '.md', '.html', '.log', '.csv')


def iter_files(roots):
    for root in roots:
        if os.path.isfile(root):
            yield root
            continue
        for dirpath, _dirs, files in os.walk(root):
            for fn in files:
                if fn.lower().endswith(SCAN_SUFFIXES):
                    yield os.path.join(dirpath, fn)


def mask(v: str) -> str:
    return f'<redacted len={len(v)}>'


def scan_text(s: str):
    """返回 [(kind, len, sha256[:12])]；已脱敏的（<redacted…>）不计。"""
    hits = []
    for m in JWT_RE.finditer(s):
        v = m.group(0)
        hits.append(('JWT', len(v), hashlib.sha256(v.encode()).hexdigest()[:12]))
    for m in KV_RE.finditer(s):
        v = m.group(2)
        if v.startswith('<redacted'):
            continue
        hits.append((m.group(1).strip('": '), len(v), hashlib.sha256(v.encode()).hexdigest()[:12]))
    return hits


def redact_text(s: str) -> tuple[str, int]:
    """纯文本替换：JWT 形状 + 白名单键的长值。返回 (新文本, 改动数)"""
    s, n1 = JWT_RE.subn(lambda m: mask(m.group(0)), s)
    s, n2 = KV_RE.subn(lambda m: m.group(1) + mask(m.group(2)) + m.group(3), s)
    return s, n1 + n2


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--redact', action='store_true', help='就地脱敏（默认只扫描）')
    ap.add_argument('--path', action='append', default=None, help='限定路径（可多次；默认扫全部证据目录）')
    args = ap.parse_args()
    roots = args.path or DEFAULT_ROOTS

    total_hits = 0
    changed_files = 0
    print(f"{'文件':<62} {'字段':<14} {'长度':<6} sha256[:12]")
    for path in iter_files(roots):
        try:
            raw = io.open(path, encoding='utf-8', newline='').read()
        except Exception:
            continue
        hits = scan_text(raw)
        for kind, ln, h in hits:
            total_hits += 1
            print(f"{path:<62} {kind:<14} {ln:<6} {h}")
        if args.redact and hits:
            new, changed = redact_text(raw)
            if changed:
                # newline='' → 原样保留文件原有行尾（不制造 CRLF/LF churn）
                io.open(path, 'w', encoding='utf-8', newline='').write(new)
                changed_files += 1

    if args.redact:
        print(f'\n已脱敏 {changed_files} 个文件')
        left = 0
        for path in iter_files(roots):
            try:
                s = io.open(path, encoding='utf-8', newline='').read()
            except Exception:
                continue
            left += len(scan_text(s))
        print(f'复扫剩余命中 = {left}')
        return 0 if left == 0 else 1

    print(f'\n命中 {total_hits} 条' + ('（无：证据文件里没有真实令牌）' if total_hits == 0 else ''))
    return 0 if total_hits == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
