import json, sys, os

page = sys.argv[1]
base = ".calicat/raw/pages/%s" % page
d = json.load(open(base + "/design.json", encoding="utf-8"))
inner = None
if isinstance(d, list) and d and isinstance(d[0], dict) and "layer_data" in d[0]:
    ld = d[0]["layer_data"]
    inner = json.loads(ld) if isinstance(ld, str) else ld
elif isinstance(d, dict):
    inner = d
out = base + "/design.tree.json"
json.dump(inner, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("wrote", out, os.path.getsize(out), "bytes")

try:
    it = json.load(open(base + "/interaction.json", encoding="utf-8"))
    s = json.dumps(it, ensure_ascii=False)
    print("interaction.json len", len(s), "->", s[:400])
except Exception as e:
    print("interaction read fail", e)

try:
    sc = json.load(open(base + "/screenshot.json", encoding="utf-8"))
    print("screenshot:", json.dumps(sc, ensure_ascii=False)[:900])
except Exception as e:
    print("screenshot read fail", e)
