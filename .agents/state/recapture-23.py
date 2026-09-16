"""重抓 序号 23 的设计帧（page-23-2 / layer_id 44006a8c-895d-4e5f-b507-f4559b644e06）并与实现所依据的留证逐字节比对。

用法: python .agents/state/recapture-23.py [out_dir]
前提: Calicat 编辑器在浏览器里打开（否则报「请先在浏览器中打开文件」）
"""
import hashlib
import os
import subprocess
import sys

REPO = r'E:/workspaces/hioas/hioas-aap-001'
FILE = '2095515676955668480'
URL = 'https://www.calicat.cn/design/%s' % FILE
SKILL = os.path.join(os.path.expanduser('~'), 'AppData', 'Local', 'hermes', 'skills', 'calicat', 'scripts', 'calicat_source.py')
PAGE_ID = 'page-23-2'
LAYER_ID = '44006a8c-895d-4e5f-b507-f4559b644e06'
out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Temp', 'aap-recap-23')


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


cmd = [sys.executable, SKILL, 'page', '--url', URL, '--layer-id', LAYER_ID,
       '--page-id', PAGE_ID, '--out', out]
print('run:', ' '.join(cmd))
r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
print('exit', r.returncode)
print((r.stdout or '')[-1500:])
print((r.stderr or '')[-800:])

new_design = os.path.join(out, 'raw', 'pages', PAGE_ID, 'design.json')
old_design = os.path.join(REPO, '.calicat', 'raw', 'pages', PAGE_ID, 'design.json')
if not os.path.exists(new_design):
    raise SystemExit('recapture produced no design.json: %s' % new_design)
hn, ho = sha(new_design), sha(old_design)
print('new design.json sha256', hn)
print('old design.json sha256', ho)
print('VERDICT:', 'BYTE-IDENTICAL' if hn == ho else 'DIFF')
if hn != ho:
    a = open(new_design, 'rb').read()
    b = open(old_design, 'rb').read()
    i = 0
    while i < min(len(a), len(b)) and a[i] == b[i]:
        i += 1
    print('new size', len(a), 'old size', len(b), 'first diff at', i)
    print('NEW:', a[max(0, i - 120):i + 160].decode('utf-8', 'replace'))
    print('OLD:', b[max(0, i - 120):i + 160].decode('utf-8', 'replace'))

# 设计 PNG
shot = os.path.join(REPO, '.agents/state/design-shots/page-23-2.png')
if os.path.exists(shot):
    print('design PNG sha256 (local)', sha(shot))
else:
    print('design PNG 未下载:', shot)
