# -*- coding: utf-8 -*-
"""逐页跑「文本叶子审计」载体页，产出 evidence/textleaf-<tag>.json。

用法:
  python .agents/state/textleaf-scan.py 8 3 2 21        # 指定序号（台账「序号」列）
  python .agents/state/textleaf-scan.py --all
  python .agents/state/textleaf-scan.py --all --from 8  # 从某序号起（按台账顺序）

口径: 每页用它**自己的 mock 目录**（否则整页 404、叶子全是错误态文案）。
"""
import csv
import io
import json
import os
import re
import shutil
import subprocess
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STATE = os.path.join(REPO, '.agents', 'state')
H5 = os.path.join(REPO, 'aap-client', 'dist', 'build', 'h5')
EVD = os.path.join(STATE, 'evidence')
TMP = os.path.join(os.environ.get('LOCALAPPDATA', '/tmp'), 'Temp')
CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe'

# 序号 → mock 目录（状态文件 §5 的对照表）
MOCK = {
    '1': 'api', '2': 'api', '3': 'api', '4': 'api', '4-v1': 'api', '5': 'api', '6': 'api',
    '7': 'api', '8': 'api', '9': 'api', '10': 'api-10-2', '10.1': 'api-10-1-2', '11': 'api-11',
    '12': 'api-12', '12-v1': 'api-12-v1', '12-v2': 'api-12-v2', '12-v3': 'api-12-v3',
    '15': 'api-15', '20': 'api-20', '21': 'api-21', '22': 'api-22', '23': 'api-23',
}
# 相对时间页面：测量紧前必须重置 mock
NEEDS_TIME_RESET = {'20': ('api-20',)}
# 带参路由：必须与各页载体页的 iframe src 一致（否则页面渲染空态 → 大量「未渲染」假象）
ROUTE_OVERRIDE = {
    '4': '/pages/credential-submit/index?id=c1',
    '5': '/pages/detecting/index?jobId=j1',
    '7': '/pages/report-failed/index?reportId=DR-7',
    '11': '/pages/model-pricing/index?itemId=qi1',
    '12': '/pages/quote-preview/index?quoteId=q7',
    '12-v3': '/pages/quote-form/success?quoteId=q9',
    '15': '/pages/contract/index?contractId=c1',
    '6': '/pages/report/index?reportId=DR-1',
}


def ledger():
    rows = list(csv.DictReader(io.open(os.path.join(STATE, 'aap-feature-status.csv'), encoding='utf-8')))
    return rows


def chrome_dump(url, out_html, tag):
    prof = os.path.join(TMP, 'chrome-tla-' + re.sub(r'[^\w.-]', '_', tag))
    cmd = [CHROME, '--headless=new', '--disable-gpu', '--no-sandbox', '--hide-scrollbars',
           '--virtual-time-budget=30000', '--user-data-dir=' + prof, '--dump-dom', url]
    with io.open(out_html, 'wb') as fh:
        subprocess.call(cmd, stdout=fh, stderr=subprocess.DEVNULL)
    return os.path.getsize(out_html)


def extract(dump_html, out_json):
    raw = io.open(dump_html, encoding='utf-8', errors='replace').read()
    m = re.search(r'MEASURE_JSON:(\{.*?\})</pre>', raw, re.S) or re.search(r'MEASURE_JSON:(\{.*)\n', raw, re.S)
    if not m:
        return None
    txt = m.group(1).split('</')[0].strip()
    try:
        data = json.loads(txt)
    except Exception:  # noqa: BLE001
        return None
    io.open(out_json, 'w', encoding='utf-8').write(json.dumps(data, ensure_ascii=False, indent=1))
    return data


def main():
    args = sys.argv[1:]
    rows = ledger()
    if '--all' in args:
        start = None
        if '--from' in args:
            start = args[args.index('--from') + 1]
        sel = []
        hit = False
        for r in rows:
            if start and r['序号'] == start:
                hit = True
            if hit or not start:
                sel.append(r)
    else:
        wanted = set(args)
        sel = [r for r in rows if r['序号'] in wanted]
    if not sel:
        print('没有匹配的台账行')
        return 1

    harness = os.path.join(STATE, 'h5-measure', '__measure-textleaf.html')
    shutil.copy(harness, os.path.join(H5, '__measure-textleaf.html'))
    if not os.path.exists(os.path.join(H5, 'index.html')):
        print('!! dist/build/h5 未构建：先 npm run build:h5')
        return 2

    port = 5400
    ok = 0
    for r in sel:
        tag, pid, route = r['序号'], r['页面ID'], r['目标路由']
        route = ROUTE_OVERRIDE.get(tag, route)
        mock = MOCK.get(tag)
        if not mock:
            print('%-7s SKIP（无 mock 目录映射）' % tag)
            continue
        reset = NEEDS_TIME_RESET.get(tag)
        if reset:
            subprocess.call([sys.executable, os.path.join(STATE, 'refresh-notification-mock.py'), '--mock', reset[0]])
        port += 1
        log = os.path.join(TMP, 'serve-tla-%s.log' % tag)
        with io.open(log, 'wb') as fh:
            srv = subprocess.Popen([sys.executable, os.path.join(STATE, 'h5-measure', 'serve.py'),
                                    H5, os.path.join(REPO, '.agents', 'state', 'h5-measure', mock),
                                    str(port)], stdout=fh, stderr=subprocess.STDOUT)
        time.sleep(1.6)
        url = 'http://127.0.0.1:%d/__measure-textleaf.html?route=%%23/%s' % (port, route.lstrip('/'))
        dump = os.path.join(TMP, 'tla-%s.html' % re.sub(r'[^\w.-]', '_', tag))
        size = chrome_dump(url, dump, tag)
        data = extract(dump, os.path.join(EVD, 'textleaf-%s.json' % tag))
        try:
            srv.kill()
        except Exception:  # noqa: BLE001
            pass
        if data is None:
            print('%-7s %-12s FAIL dump=%dB（无 MEASURE_JSON）' % (tag, pid, size))
            continue
        ok += 1
        print('%-7s %-12s leafs=%-4s docH=%-6s dump=%dB' % (tag, pid, len(data.get('leafs') or []), data.get('docH'), size))
    print('完成 %d/%d 页' % (ok, len(sel)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
