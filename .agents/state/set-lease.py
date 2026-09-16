"""set-lease.py — 把状态文件第 2 行的租约改成 <holder> until <until>（EOL 安全：整文件保持 CRLF）。

用法: python .agents/state/set-lease.py <holder> <until>
     python .agents/state/set-lease.py free -
"""
import io
import sys

P = 'E:/workspaces/hioas/hioas-aap-001/.agents/state/aap-tdd-state.md'

holder = sys.argv[1]
until = sys.argv[2]
s = io.open(P, encoding='utf-8', newline='').read()
nl = '\r\n' if '\r\n' in s else '\n'
lines = s.replace('\r\n', '\n').split('\n')
hit = False
for i, line in enumerate(lines[:5]):
    if line.startswith('LEASE:'):
        print('old:', line)
        lines[i] = 'LEASE: %s until %s' % (holder, until)
        print('new:', lines[i])
        hit = True
if not hit:
    raise SystemExit('LEASE line not found in the first 5 lines')
io.open(P, 'w', encoding='utf-8', newline='').write(nl.join(lines))
print('written, eol=%r' % nl)
