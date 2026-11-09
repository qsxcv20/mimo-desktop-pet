#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""enum_all.py — 枚举所有顶层窗口 + 进程，定位 MiMo。"""
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass  # pythonw.exe 下 sys.stdout 是 None
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mimo_host as H

print("=== 所有 Chrome/顶层窗口 ===")
for h in H.enum_top():
    cls = H._cls(h)
    txt = H._text(h)
    pid = H._pid(h)
    vis = H.user32.IsWindowVisible(h)
    st = H._style(h)
    icon = H.user32.IsIconic(h)
    r = H._rect(h)
    if not txt and cls == "Progman":
        continue
    print("%-12s vis=%-5s icon=%-5s pid=%-6d cls=%-26s rect=%-28s %r"
          % (hex(h), vis, icon, pid, cls, r, txt[:40]))

print("\n=== MiMo 进程 ===")
try:
    import psutil
    for p in psutil.process_iter(["pid", "name", "exe"]):
        try:
            n = (p.info["name"] or "").lower()
            if "mimo" in n or "xiaomi" in n:
                print("  pid=%-6d name=%-22s exe=%s"
                      % (p.info["pid"], p.info["name"], p.info["exe"]))
        except Exception:
            pass
except Exception as e:
    print("  psutil 不可用:", e)
