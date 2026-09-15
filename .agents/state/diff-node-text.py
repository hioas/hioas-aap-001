import re
import sys
from pathlib import Path

def texts(p):
    s = Path(p).read_text(encoding="utf-8")
    return re.findall(r"TEXT='((?:[^'\\]|\\.)*)'", s)

a = texts(sys.argv[1])
b = texts(sys.argv[2])
sa, sb = set(a), set(b)
print("A:", len(a), "B:", len(b))
print("only in A:", [x for x in a if x not in sb])
print("only in B:", [x for x in b if x not in sa])
