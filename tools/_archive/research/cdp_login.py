#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""cdp_login.py — 读取 MiMo 内嵌的小米账号登录页当前状态，判断是需要密码还是已登录待确认。"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pet"))

from mimo_cdp import MiMoCDP  # noqa: E402

PROBES = [
    ("url", "location.href"),
    ("title", "document.title"),
    ("body文本", "document.body ? document.body.innerText.replace(/\\s+/g,' ').slice(0,700) : null"),
    ("输入框", "(()=>{const i=[...document.querySelectorAll('input')].map(e=>"
               "({type:e.type,name:e.name,ph:e.placeholder,val:e.value?'*'.repeat(e.value.length):''}));"
               "return i})()"),
    ("按钮", r"""(()=>{const b=[...document.querySelectorAll('button,a[role=button],[class*=btn]')]
                .slice(0,25).map(e=>(e.innerText||'').trim()).filter(Boolean);
                return [...new Set(b)]})()"""),
    ("cookie域", "document.cookie.slice(0,400)"),
]

if __name__ == "__main__":
    c = MiMoCDP()
    lt = c.pick_login_target()
    if not lt:
        print("没有找到 account.xiaomi.com 登录 target")
        raise SystemExit(1)
    print("登录 target:", lt.get("title"), "|", (lt.get("url") or "")[:120])
    print()
    for name, expr in PROBES:
        try:
            v = c.evaluate(expr, timeout=8, target=lt)
        except Exception as e:
            v = "ERR: %s" % e
        print(">> %-10s %s" % (name, json.dumps(v, ensure_ascii=False)))
