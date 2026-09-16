import io
import json
import sys

d = json.load(io.open(sys.argv[1], encoding='utf-8'))
for k in d:
    if k.startswith('phase') and isinstance(d[k], dict) and 'message' in d[k]:
        print(k, '=>', d[k].get('message'))
        print((d[k].get('stack') or '')[:600])
