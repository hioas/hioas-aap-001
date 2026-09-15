import json, sys

path = sys.argv[1]
maxdepth = int(sys.argv[2]) if len(sys.argv) > 2 else 10
d = json.load(open(path, encoding="utf-8"))
roots = d if isinstance(d, list) else (d.get("nodes") or d.get("layers") or d.get("children") or [d])


def g(n, *ks):
    for k in ks:
        if n.get(k) not in (None, "", []):
            return n[k]
    return None


def fill_hex(n):
    f = n.get("fills") or n.get("fill")
    if isinstance(f, list) and f and isinstance(f[0], dict):
        return f[0].get("color") or f[0].get("hex") or ""
    if isinstance(f, dict):
        return f.get("color") or f.get("hex") or ""
    if isinstance(f, str):
        return f
    return ""


def walk(n, depth):
    if depth > maxdepth:
        return
    txt = g(n, "characters", "text", "content") or ""
    if isinstance(txt, str):
        txt = txt.replace("\n", "\\n")
    typ = n.get("type", "")
    parts = ["  " * depth + "%s|%s" % (typ, n.get("id") or n.get("layerId") or "-"),
             "name=%s" % (n.get("name") or "")]
    if txt:
        parts.append('T="%s"' % txt[:100])
    wh = []
    for k in ("width", "height"):
        v = n.get(k)
        if isinstance(v, dict):
            v = v.get("value", v)
        if v not in (None, ""):
            wh.append("%s=%s" % (k[0], v))
    if wh:
        parts.append(" ".join(wh))
    st = []
    for k in ("layoutMode", "itemSpacing", "padding", "cornerRadius", "borderRadius", "fontSize",
              "fontWeight", "textAlign", "lineHeight", "color"):
        v = n.get(k)
        if v not in (None, "", []):
            st.append("%s=%s" % (k, v))
    fh = fill_hex(n)
    if fh:
        st.append("fill=%s" % fh)
    if n.get("fontFill"):
        st.append("fontFill=%s" % n["fontFill"])
    if n.get("stroke"):
        st.append("stroke=%s" % n["stroke"])
    if n.get("effects"):
        st.append("effects=%s" % n["effects"])
    if n.get("backgroundColor"):
        st.append("bg=%s" % n["backgroundColor"])
    if st:
        parts.append("[" + " ".join(str(x) for x in st) + "]")
    print(" ".join(parts))
    for c in (n.get("children") or []):
        walk(c, depth + 1)


for r in roots:
    walk(r, 0)
