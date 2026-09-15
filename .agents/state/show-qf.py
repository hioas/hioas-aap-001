#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""序号 12-v1 取数：打印 measure JSON 的关键字段（phase1 结构 + phase2/phase3 交互结论）。

用法：python .agents/state/show-qf.py <measure.json> [字段名 …]
"""
import json
import sys

KEYS = [
    'innerWidth', 'docScrollWidth', 'docScrollHeight', 'overflowingCount', 'missingTexts',
    'nav', 'navPad', 'stepCard', 'steps', 'stepDots', 'stepDotBgs', 'stepActive', 'stepLine',
    'cards', 'cardHead', 'required', 'nameLabel', 'nameBox', 'nameCounter', 'dividers',
    'quoteNoLabel', 'quoteNoTag', 'quoteNoTagBg', 'quoteNoBox', 'quoteNoBoxBg', 'samplePill',
    'quoteNoHint', 'credLabel', 'credSelect', 'credKeybox', 'credValue', 'credHint',
    'chipModel', 'chipModelText', 'chipModelBg', 'empty', 'emptyBg', 'emptyIcon', 'emptyTitle',
    'emptyDesc', 'tip', 'tipBg', 'tipText', 'noticeTitle', 'noticeDots', 'noticeTexts',
    'bar', 'barPad', 'barHint', 'barRow', 'draftBtn', 'saveBtn', 'modelRows',
    'inputCount', 'tabbarExists', 'pageBg', 'emptyPad', 'tipPad', 'cardPadding', 'bodyPad', 'bodyGap'
]


def main() -> None:
    path = sys.argv[1]
    wanted = sys.argv[2:] or KEYS
    data = json.load(open(path, encoding='utf-8'))
    if isinstance(data, dict) and 'MEASURE_JSON' in data:
        data = data['MEASURE_JSON']
    ph = data.get('phase1')
    if ph is None:
        print('!! 无 phase1，顶层键：', list(data.keys()))
        return
    for k in wanted:
        print(f'{k} = {json.dumps(ph.get(k), ensure_ascii=False)}')
    for other in ('phase2', 'phase3'):
        if other in data:
            print(f'--- {other} ---')
            print(json.dumps(data[other], ensure_ascii=False))


if __name__ == '__main__':
    main()
