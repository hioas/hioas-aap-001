"""Parse calicat get_design_page_list output into id/name pairs."""
import json
import sys

p = sys.argv[1]
raw = open(p, encoding="utf-8", errors="replace").read()
obj = json.loads(raw)
inner = json.loads(obj["content"][0]["text"])
pages = inner["result"]["page_list"]
for pg in pages:
    print(pg["layer_id"], "|", pg["name"])
