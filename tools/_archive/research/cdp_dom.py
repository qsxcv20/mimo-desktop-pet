#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""cdp_dom.py — 通过 CDP 读取 MiMo 渲染层当前的 DOM 文本，判断是正常界面还是错误页。"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pet"))

from mimo_cdp import MiMoCDP  # noqa: E402

PROBES = [
    ("title", "document.title"),
    ("url", "location.href"),
    ("readyState", "document.readyState"),
    ("节点数", "document.querySelectorAll('*').length"),
    ("body文本(前600)", "document.body ? document.body.innerText.slice(0,600) : null"),
    ("root子节点数",
     "(()=>{const r=document.getElementById('root')||document.querySelector('#app');"
     "return r?r.children.length:null})()"),
    ("可见顶层块数",
     "(()=>{let n=0;document.querySelectorAll('body *').forEach(e=>{const r=e.getBoundingClientRect();"
     "if(r.width>40&&r.height>20&&getComputedStyle(e).visibility!=='hidden')n++});return n})()"),
    ("重试按钮",
     "(()=>{const a=[...document.querySelectorAll('a,button,span')].filter(e=>e.textContent.trim()==='重试');"
     "return a.length?a.map(e=>e.className+' | '+(e.parentElement?e.parentElement.className:'')):null})()"),
    ("body背景", "getComputedStyle(document.body).backgroundColor"),
    ("body子HTML长度", "document.body ? document.body.innerHTML.length : 0"),
]

if __name__ == "__main__":
    c = MiMoCDP()
    if not c.available():
        print("调试端口不可用")
        raise SystemExit(1)
    for t in c.targets():
        print("target: %-8s %-26s %s" % (t.get("type"), (t.get("title") or "")[:26],
                                         (t.get("url") or "")[:80]))
    print()
    for name, expr in PROBES:
        try:
            v = c.evaluate(expr, timeout=8)
        except Exception as e:
            v = "ERR: %s" % e
        if isinstance(v, str) and len(v) > 600:
            v = v[:600] + "..."
        print(">> %-16s %s" % (name, json.dumps(v, ensure_ascii=False)))
