"""临时：打印某轮实测 JSON 的逐相 checks 概览 + 失败清单（兼容 checkFails 为字符串数组的老探针）。"""
import json
import sys

path = sys.argv[1]
d = json.load(open(path, encoding='utf-8'))
for ph in sorted(d.keys()):
    p = d[ph]
    if not isinstance(p, dict):
        continue
    fails = p.get('checkFails') or []
    print('%s: checks=%s fails=%s docH=%s overflow=%s' % (
        ph, p.get('checkCount'), p.get('checkFailCount'), p.get('docScrollHeight'), p.get('overflowingCount')))
    for f in fails:
        if isinstance(f, dict):
            print('    FAIL %s: got %s want %s' % (f.get('k'), json.dumps(f.get('got'), ensure_ascii=False), json.dumps(f.get('want'), ensure_ascii=False)))
        else:
            print('    FAIL %s' % f)
