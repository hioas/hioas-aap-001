import io
import json
import sys

d = json.load(io.open(sys.argv[1], encoding='utf-8'))
print('top keys:', list(d.keys()))
for k, v in d.items():
    if isinstance(v, dict):
        if 'checkCount' in v or 'error' in v:
            print('--', k, 'checkCount=', v.get('checkCount'), 'fails=', v.get('checkFailCount'), 'error=', v.get('error'))
            for f in (v.get('checkFails') or [])[:80]:
                print('   FAIL', f.get('k'), '| got', repr(f.get('got')), '| want', repr(f.get('want')))
        else:
            print('--', k, 'keys=', list(v.keys())[:12])
    else:
        print('--', k, '=', v)
