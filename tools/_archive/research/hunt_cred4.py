#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""hunt_cred4.py — 只扫 MiMo userData（跳过 runtime-res），找账号凭据。"""
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

UD = os.path.join(os.environ["APPDATA"], "Xiaomi MiMo")
SKIP = {"runtime-res", "Cache", "Code Cache", "GPUCache", "DawnCache",
        "blob_storage", "Service Worker", "Crashpad", "logs", "IndexedDB",
        "blob_storage", "Network Persistent State"}

PAT = re.compile(rb'(access_?token|refresh_?token|userToken|sso_?token|'
                 rb'"token"|xiaomiToken|accountToken|passportToken)')
JWT = re.compile(rb'[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}')

n = 0
for dp, dns, fns in os.walk(UD):
    dns[:] = [d for d in dns if d not in SKIP]
    for fn in fns:
        p = os.path.join(dp, fn)
        try:
            sz = os.path.getsize(p)
        except Exception:
            continue
        if sz > 60 * 1024 * 1024:
            continue
        rel = os.path.relpath(p, UD)
        try:
            with open(p, "rb") as f:
                data = f.read()
        except Exception:
            continue
        hits = PAT.findall(data)
        jwts = JWT.findall(data)
        if hits or jwts:
            n += 1
            print("\n### %s  (%d bytes)" % (rel, sz))
            for h in sorted(set(hits))[:6]:
                print("    kw:", h.decode("ascii", "replace"))
            for j in jwts[:3]:
                print("    jwt:", j[:70].decode("ascii", "replace"))
            if not jwts:
                # 打印命中关键词的上下文
                for m in list(PAT.finditer(data))[:3]:
                    a = max(0, m.start() - 90)
                    b = min(len(data), m.end() + 160)
                    print("    ctx:", data[a:b].decode("utf-8", "replace").replace("\n", " "))
print("\n命中文件数:", n)

print("\n\n=== userData 全部小文件清单 ===")
for dp, dns, fns in os.walk(UD):
    dns[:] = [d for d in dns if d not in SKIP]
    for fn in fns:
        p = os.path.join(dp, fn)
        try:
            sz = os.path.getsize(p)
        except Exception:
            continue
        if sz < 200000:
            print("  %8d %s" % (sz, os.path.relpath(p, UD)))
