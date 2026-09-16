"""Crude JS brace-depth scanner: reports the first line where depth goes negative and
the depth at EOF, skipping '...'/"..."/`...` strings, // and /* */ comments."""
import io
import re
import sys

path = sys.argv[1]
src = io.open(path, encoding="utf-8").read()

# strip strings and comments (crude: no template interpolation handling)
s = src
s = re.sub(r"//[^\n]*", "", s)
s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
s = re.sub(r"'(?:\\.|[^'\\\n])*'", "''", s)
s = re.sub(r'"(?:\\.|[^"\\\n])*"', '""', s)
s = re.sub(r"`(?:\\.|[^`\\])*`", "``", s)

depth = 0
line = 1
first_neg = None
for ch in s:
    if ch == "\n":
        line += 1
    elif ch == "{":
        depth += 1
    elif ch == "}":
        depth -= 1
        if depth < 0 and first_neg is None:
            first_neg = line
print("final depth", depth, "first negative at line", first_neg, "total lines", line)
if first_neg:
    lines = s.split("\n")
    for i in range(max(0, first_neg - 4), min(len(lines), first_neg + 2)):
        print(i + 1, "|", lines[i][:160])
