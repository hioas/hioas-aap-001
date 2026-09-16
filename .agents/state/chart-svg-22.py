# -*- coding: utf-8 -*-
"""序号 22：从 H5 产物 DOM 里取出趋势图的 SVG data-URI 并解码打印（判「实现画法 ↔ 设计内联 SVG」等价）。

用法: python .agents/state/chart-svg-22.py [port]
"""
import base64
import io
import os
import re
import subprocess
import sys
import time

REPO = r'E:/workspaces/hioas/hioas-aap-001'
H5 = os.path.join(REPO, 'aap-client', 'dist', 'build', 'h5')
MOCK = os.path.join(REPO, '.agents', 'state', 'h5-measure', 'api-22')
SERVE = os.path.join(REPO, '.agents', 'state', 'h5-measure', 'serve.py')
CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe'
TMP = os.path.join(os.environ.get('LOCALAPPDATA', '/tmp'), 'Temp')
port = int(sys.argv[1]) if len(sys.argv) > 1 else 5399

srv = subprocess.Popen([sys.executable, SERVE, H5, MOCK, str(port)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(3)
try:
    url = 'http://127.0.0.1:%d/index.html#/pages/usage/index' % port
    r = subprocess.run([CHROME, '--headless=new', '--disable-gpu', '--no-sandbox', '--hide-scrollbars',
                        '--virtual-time-budget=20000', '--user-data-dir=' + os.path.join(TMP, 'chrome-chart22'),
                        '--dump-dom', url], capture_output=True, text=True, encoding='utf-8', errors='replace')
    dom = r.stdout or ''
    print('dom bytes', len(dom))
    uris = re.findall(r'data:image/svg\+xml;base64,([A-Za-z0-9+/=]+)', dom)
    print('data-URI 数量 =', len(uris))
    for i, u in enumerate(uris):
        svg = base64.b64decode(u).decode('utf-8', 'replace')
        print('--- svg[%d] len=%d' % (i, len(svg)))
        print(svg)
finally:
    srv.terminate()
