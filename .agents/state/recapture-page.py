"""重抓某一帧的设计数据并与实现所依据的留证逐字节比对（通用版）。

用法: python .agents/state/recapture-page.py <page-id> <layer-id> [out_dir]
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
PAGE_ID = sys.argv[1]
LAYER_ID = sys.argv[2]
out = sys.argv[3] if len(sys.argv) > 3 else os.path.join(
    os.environ.get('LOCALAPPDATA', ''), 'Temp', 'aap-recap-%s' % PAGE_ID)


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


cmd = [sys.executable, SKILL, 'page', '--url', URL, '--layer-id', LAYER_ID,
       '--page-id', PAGE_ID, '--out', out]
print('run:', ' '.join(cmd))
r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
print('exit', r.returncode)
print((r.stdout or '')[-1500:])
print((r.stderr or '')[-800:])

for name in ('design.json', 'design.tree.json', 'screenshot.json'):
    new = os.path.join(out, 'raw', 'pages', PAGE_ID, name)
    old = os.path.join(REPO, '.calicat', 'raw', 'pages', PAGE_ID, name)
    if not os.path.exists(new):
        print('%s: MISSING in recapture' % name)
        continue
    hn, ho = sha(new), sha(old)
    print('%s: new=%s old=%s -> %s' % (name, hn[:12], ho[:12], 'BYTE-IDENTICAL' if hn == ho else 'DIFF'))
    if hn != ho and name == 'design.json':
        a = open(new, 'rb').read()
        b = open(old, 'rb').read()
        i = 0
        while i < min(len(a), len(b)) and a[i] == b[i]:
            i += 1
        print('size new', len(a), 'old', len(b), 'first diff at', i)
        print('NEW:', a[max(0, i - 150):i + 200].decode('utf-8', 'replace'))
        print('OLD:', b[max(0, i - 150):i + 200].decode('utf-8', 'replace'))
