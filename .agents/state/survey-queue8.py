import os, re, glob, json
root = r'E:\workspaces\hioas\hioas-aap-001\.agents\state\h5-measure'
for f in sorted(glob.glob(os.path.join(root, '__measure*.html'))):
    s = open(f, encoding='utf-8', errors='replace').read()
    routes = re.findall(r"['\"](/pages/[a-zA-Z0-9_\-/]+)['\"]", s)
    chk = s.count('chk(')
    has_chk = 'function chk' in s or 'const chk' in s
    print(os.path.basename(f), '| bytes', len(s), '| chk-calls', chk, '| chk-def', has_chk, '| routes', sorted(set(routes))[:4])
