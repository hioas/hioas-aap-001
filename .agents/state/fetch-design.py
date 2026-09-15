"""下载设计帧截图（页面级）。

用法：python .agents/state/fetch-design.py <page-id> [输出文件名]

从 .calicat/raw/pages/<page-id>/screenshot.json 读取 COS URL 并下载到
%s/Temp/design-<page-id>.png 形式（纯 ASCII 路径，避开 MSYS 中文参数转码），
然后打印「宽x高 字节数」，供 png-bands / png-ink / pngdump 等像素量尺使用。
"""
import json
import os
import sys
import urllib.request

root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
page = sys.argv[1]
out = sys.argv[2] if len(sys.argv) > 2 else None

meta = json.load(open(os.path.join(root, '.calicat', 'raw', 'pages', page, 'screenshot.json'), encoding='utf-8'))
urls = json.loads(meta['result'])
url = urls[0]
if not out:
    tmp = os.environ.get('LOCALAPPDATA', os.path.expanduser('~')) + '/Temp'
    os.makedirs(tmp, exist_ok=True)
    out = os.path.join(tmp, 'design-%s.png' % page)

req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req, timeout=60) as r:
    data = r.read()
with open(out, 'wb') as f:
    f.write(data)

# 读 PNG 头拿宽高
w = int.from_bytes(data[16:20], 'big')
h = int.from_bytes(data[20:24], 'big')
print('file=%s' % out)
print('size=%dx%d bytes=%d' % (w, h, len(data)))
