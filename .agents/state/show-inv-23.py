import json
inv = json.load(open('.calicat/inventory.json', encoding='utf-8'))
print('canvases:', [c.get('id') for c in inv.get('canvases', [])])
for p in inv['pages']:
    if p['id'] in ('page-23-2', 'page-22-2', 'page-21-2'):
        print(json.dumps(p, ensure_ascii=False, indent=1))
print('--- raw pages.json sample ---')
raw = json.load(open('.calicat/raw/pages.json', encoding='utf-8'))
print(type(raw))
s = json.dumps(raw, ensure_ascii=False)
print(s[:800])
