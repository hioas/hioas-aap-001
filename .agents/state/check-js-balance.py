import io
import sys

p = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\laitz\AppData\Local\Temp\probe10.js"
s = io.open(p, encoding="utf-8").read()
print("lines", s.count("\n"))
print("brace open/close", s.count("{"), s.count("}"))
print("paren open/close", s.count("("), s.count(")"))
print("bracket open/close", s.count("["), s.count("]"))
print("--- last 400 chars ---")
print(s[-400:])
