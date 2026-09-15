import csv, sys
path = sys.argv[1] if len(sys.argv) > 1 else '.agents/state/aap-feature-status.csv'
rows = list(csv.DictReader(open(path, encoding='utf-8')))
for r in rows:
    print(' | '.join([r.get('序号', ''), r.get('页面ID', ''), r.get('页面名', ''), r.get('目标路由', ''), r.get('状态', '')]))
