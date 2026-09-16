import json
import sys

path = sys.argv[1]
want = sys.argv[2]
limit = int(sys.argv[3]) if len(sys.argv) > 3 else 4000

with open(path, encoding="utf-8") as fh:
    tree = json.load(fh)


def walk(node):
    if isinstance(node, dict):
        if node.get("name") == want:
            print("=" * 20, want, "=" * 20)
            print(json.dumps(node, ensure_ascii=False, indent=1)[:limit])
        for value in node.values():
            walk(value)
    elif isinstance(node, list):
        for value in node:
            walk(value)


walk(tree)
