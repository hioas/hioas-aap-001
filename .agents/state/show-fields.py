"""临时：打印某轮实测 JSON 里感兴趣的字段（避免 cron 里用 heredoc/内联脚本）。"""
import json
import sys

path = sys.argv[1]
phase = sys.argv[2]
keys = sys.argv[3:]

d = json.load(open(path, encoding='utf-8'))
p = d.get(phase)
if p is None:
    print('no phase', phase, 'have', list(d.keys()))
    sys.exit(1)
if not keys:
    keys = list(p.keys())
for k in keys:
    print(k, '=', json.dumps(p.get(k), ensure_ascii=False))
