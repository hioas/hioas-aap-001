"""序号 12-v2（page-apikey）measure 取数：按 phase 打印关键字段，便于逐项与设计对账。

用法：
  python .agents/state/show-a12v2.py <measure.json>                  # 概览（phase1 关键 + phase2/3/4 交互结论）
  python .agents/state/show-a12v2.py <measure.json> 1 [字段…]        # 指定 phase 打印指定字段（缺省打印全部非空）
"""
import json
import sys

path = sys.argv[1]
phase = sys.argv[2] if len(sys.argv) > 2 else None
fields = sys.argv[3:]

acc = json.load(open(path, encoding='utf-8'))

if phase:
    data = acc.get('phase%s' % phase, {})
    keys = fields or [k for k in data if data[k] not in (None, [], '', 0) or k in ('overflowingCount', 'inputCount', 'pickedCount')]
    for k in keys:
        print('%s = %s' % (k, json.dumps(data.get(k), ensure_ascii=False)))
else:
    p1 = acc.get('phase1', {})
    print('== phase1 ==')
    for k in ['innerWidth', 'docScrollWidth', 'docScrollHeight', 'overflowingCount', 'missingTexts', 'cards',
              'credSelect', 'credPanel', 'optionRows', 'optionTitles', 'optionSubs', 'optionSelected',
              'recTags', 'envTags', 'pickedCount', 'panelAction', 'panelActionText', 'empty', 'emptyDescText',
              'chipModelText', 'stepCardCount', 'tipCount', 'noticeCardCount', 'bar', 'draftBtn', 'saveBtn',
              'inputCount', 'tabbarExists', 'iframeHeightForShot']:
        print('%s = %s' % (k, json.dumps(p1.get(k), ensure_ascii=False)))
    for n in [2, 3, 4]:
        p = acc.get('phase%s' % n)
        if p:
            print('== phase%s ==' % n)
            for k, v in p.items():
                print('%s = %s' % (k, json.dumps(v, ensure_ascii=False)))
