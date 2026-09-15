"""把 .calicat/raw/pages/<page-id>/design.json 的 layer_data 展开成 design.tree.json。

用法: python .agents/state/extract-tree.py page-2-b
"""
import json
import sys
from pathlib import Path

page_id = sys.argv[1]
base = Path(".calicat/raw/pages") / page_id
design = json.loads((base / "design.json").read_text(encoding="utf-8"))
if isinstance(design, dict) and design.get("content"):
    # MCP 形态
    text = design["content"][0]["text"]
    design = json.loads(text)

if isinstance(design, list) and design and isinstance(design[0], dict) and "layer_data" in design[0]:
    inner = json.loads(design[0]["layer_data"]) if isinstance(design[0]["layer_data"], str) else design[0]["layer_data"]
else:
    inner = design

out = base / "design.tree.json"
out.write_text(json.dumps(inner, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"写出 {out} ({out.stat().st_size} bytes)")
