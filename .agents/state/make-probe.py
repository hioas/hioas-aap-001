"""在 H5 构建产物的 index.html 副本上注入探针脚本，用于在**顶层窗口**（与截图同样的布局视口）实测 DOM 几何。

用法：python .agents/state/make-probe.py <aap-client/dist/build/h5> <probe文件名> <route-hash>
"""
import sys, os

root = sys.argv[1]
out_name = sys.argv[2] if len(sys.argv) > 2 else "__probe.html"
src = open(os.path.join(root, "index.html"), encoding="utf-8").read()

PROBE = """
<pre id="__probe" style="position:absolute;left:-9999px">pending</pre>
<script>
  function __collect() {
    try {
      var doc = document, win = window;
      function rect(s) {
        var e = doc.querySelector(s); if (!e) return null;
        var b = e.getBoundingClientRect();
        return { x: Math.round(b.x), right: Math.round(b.right), w: Math.round(b.width), top: Math.round(b.top), bottom: Math.round(b.bottom) };
      }
      var over = [];
      doc.querySelectorAll('*').forEach(function (el) {
        var r = el.getBoundingClientRect();
        if (r.width > 0 && r.right > win.innerWidth + 0.5) {
          over.push({ cls: String(el.className || el.tagName).slice(0, 60), right: Math.round(r.right) });
        }
      });
      var out = {
        innerWidth: win.innerWidth,
        innerHeight: win.innerHeight,
        docClientWidth: doc.documentElement.clientWidth,
        docScrollWidth: doc.documentElement.scrollWidth,
        bodyScrollWidth: doc.body.scrollWidth,
        docScrollHeight: Math.max(doc.documentElement.scrollHeight, doc.body.scrollHeight),
        overflowingCount: over.length,
        overflowing: over.slice(0, 10),
        cred: rect('.cred'),
        topbar: rect('.cred__topbar'),
        help: rect('[data-testid="help-btn"]'),
        back: rect('[data-testid="back-btn"]'),
        listTotal: rect('[data-testid="list-total"]'),
        card: rect('.cred-card'),
        tabbar: rect('.tabbar'),
        rowDot: rect('.cred-row__dot'),
        viewCol: rect('.cred-row__view'),
        listTotalText: (function () { var e = doc.querySelector('[data-testid="list-total"]'); return e ? e.textContent : null })(),
        rowCount: doc.querySelectorAll('[data-testid="cred-row"]').length,
        reportCount: doc.querySelectorAll('[data-testid^="row-report-"]').length,
        chipCount: doc.querySelectorAll('.chip').length
      };
      document.getElementById('__probe').textContent = 'PROBE_JSON:' + JSON.stringify(out);
    } catch (e) {
      document.getElementById('__probe').textContent = 'PROBE_JSON:{"error":"' + e.message + '"}';
    }
  }
  setTimeout(__collect, 4000);
</script>
</body>"""

html = src.replace("</body>", PROBE, 1)
path = os.path.join(root, out_name)
open(path, "w", encoding="utf-8").write(html)
print("wrote", path, len(html), "bytes")
