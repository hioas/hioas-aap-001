import json, sys
inv = json.load(open('.calicat/inventory.json', encoding='utf-8'))
target = sys.argv[1] if len(sys.argv) > 1 else 'page-21-2'
hits = []


def walk(o, path=''):
    if isinstance(o, dict):
        vals = {k: v for k, v in o.items() if not isinstance(v, (dict, list))}
        blob = json.dumps(vals, ensure_ascii=False)
        if target in blob or 'mine' in blob:
            hits.append((path, blob[:500]))
        for k, v in o.items():
            walk(v, path + '/' + str(k))
    elif isinstance(o, list):
        for i, v in enumerate(o):
            walk(v, path + '[%d]' % i)


walk(inv)
print('hits:', len(hits))
for p, b in hits[:20]:
    print(p, '=>', b)
