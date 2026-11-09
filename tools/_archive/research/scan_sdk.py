#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""scan_sdk.py — 看官方 @mimo-ai/sdk 里有没有额度接口与鉴权方式。"""
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = r"C:\Users\yang2\.config\mimocode\node_modules\@mimo-ai"
for pkg in ("sdk", "plugin"):
    base = os.path.join(ROOT, pkg)
    print("\n############ %s ############" % pkg)
    for dp, dns, fns in os.walk(base):
        dns[:] = [d for d in dns if d != "node_modules"]
        for fn in fns:
            p = os.path.join(dp, fn)
            print("  %8d %s" % (os.path.getsize(p), os.path.relpath(p, base)))

print("\n\n############ sdk 里 usage/subscription 相关 ############")
import subprocess
for dp, dns, fns in os.walk(os.path.join(ROOT, "sdk")):
    for fn in fns:
        if not fn.endswith((".js", ".ts", ".json")):
            continue
        p = os.path.join(dp, fn)
        try:
            s = open(p, "r", encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        hits = set()
        for pat in (r'"/[a-zA-Z0-9_\-/.]*(?:usage|subscription|balance|tokenPlan|quota)[a-zA-Z0-9_\-/.]*"',
                    r'\b(usage|subscription|balance|tokenPlan|quota)[A-Za-z]*\s*[:(=]'):
            for m in re.finditer(pat, s):
                hits.add(m.group(0)[:120])
        if hits:
            print("\n-- %s" % os.path.relpath(p, ROOT))
            for h in sorted(hits)[:40]:
                print("     ", h)
