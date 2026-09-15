#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""序号 23「我的设置」取数打印器：show-s23.py <measure.json> [字段名…]（无参打印关键字段）

用法:
  python .agents/state/show-s23.py .agents/state/evidence/measure-序号23-run1.json
  python .agents/state/show-s23.py <json> accountCard notifyCard smsSwitchRect
"""
import json
import sys

DEFAULT_KEYS = [
    'innerWidth', 'docScrollWidth', 'docScrollHeight', 'overflowingCount', 'missingTexts', 'needTextCount',
    'navRect', 'accountCard', 'accountHeadRect', 'accountRows', 'accountLabels', 'accountValues',
    'accountSeps', 'accountPills', 'accountChevrons', 'accountTargets',
    'notifyCard', 'notifyRows', 'notifyTitles', 'notifyDescs', 'notifySepRect',
    'smsSwitchRect', 'smsSwitchDataOn', 'switchKnobRect', 'subscribeBadgeRect',
    'entryCard', 'entryRows', 'entryLabels', 'entryTones', 'entryIconRects', 'entrySepRects',
    'footerRect', 'footerVersionRect', 'footerCopyrightRect',
    'inputCount', 'tabbarExists', 'cardCount', 'accountRowCount', 'notifyRowCount', 'entryRowCount', 'switchCount'
]


def main():
    path = sys.argv[1]
    keys = sys.argv[2:] or DEFAULT_KEYS
    data = json.load(open(path, encoding='utf-8'))
    for phase in sorted(data.keys()):
        print('=== %s ===' % phase)
        payload = data[phase]
        for key in keys:
            if key in payload:
                print('  %s = %s' % (key, json.dumps(payload[key], ensure_ascii=False)))
        if phase != 'phase1':
            for key in payload:
                if key not in keys:
                    print('  %s = %s' % (key, json.dumps(payload[key], ensure_ascii=False)))


if __name__ == '__main__':
    main()
