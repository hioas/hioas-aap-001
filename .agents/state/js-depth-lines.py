"""逐行大括号净值（忽略字符串/正则/注释），定位载体页内联脚本不闭合的位置。

用法：python .agents/state/js-depth-lines.py <extracted.js> [from] [to]
"""
import io
import re
import sys

path = sys.argv[1]
start = int(sys.argv[2]) if len(sys.argv) > 2 else 1
end = int(sys.argv[3]) if len(sys.argv) > 3 else 10 ** 9

with io.open(path, encoding="utf-8") as fh:
    lines = fh.read().split("\n")

depth = 0
prev = 0
for i, line in enumerate(lines, 1):
    # 去掉字符串字面量、模板串与正则（近似：'...'、"..."、/.../）
    s = re.sub(r"'(?:\\.|[^'\\])*'", "''", line)
    s = re.sub(r'"(?:\\.|[^"\\])*"', '""', s)
    s = re.sub(r"//.*$", "", s)
    s = re.sub(r"/[^\s/][^\n]*?/[gimsuy]*", "//", s)
    d = s.count("{") - s.count("}")
    if d < 0:
        print("NEGATIVE at line %d (depth %d -> %d): %s" % (i, depth, depth + d, line.strip()[:120]))
    depth += d
    if start <= i <= end:
        if d != 0 or i >= len(lines) - 12:
            print("%5d  d=%+d  depth=%d  %s" % (i, d, depth, line.strip()[:110]))
    prev = depth if False else prev
print("final depth", depth)
