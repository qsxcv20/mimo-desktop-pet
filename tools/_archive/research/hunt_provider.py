#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""hunt_provider.py — 列 MiMo userData 全部数据文件 + 搜 provider 凭据文件名。"""
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

UD = os.path.join(os.environ["APPDATA"], "Xiaomi MiMo")
BIG = {"runtime-res", "resources", "engine-config", "Cache", "Code Cache",
       "GPUCache", "DawnCache", "blob_storage", "Service Worker", "Crashpad",
       "logs", "git-version-store", "bin"}

print("=== userData 文件清单（排除大目录）===")
files = []
for dp, dns, fns in os.walk(UD):
    dns[:] = [d for d in dns if d not in BIG]
    for fn in fns:
        p = os.path.join(dp, fn)
        try:
            sz = os.path.getsize(p)
        except Exception:
            continue
        files.append((sz, os.path.relpath(p, UD)))
for sz, rel in sorted(files, key=lambda x: -x[0])[:120]:
    print("  %10d  %s" % (sz, rel))

print("\n=== 搜 provider/连接 相关文件名 ===")
for dp, dns, fns in os.walk(UD):
    dns[:] = [d for d in dns if d not in BIG]
    for fn in fns:
        low = fn.lower()
        if any(k in low for k in ("provider", "connect", "authoriz", "account",
                                  "auth", "credential", "token", "login")):
            print("  %s" % os.path.relpath(os.path.join(dp, fn), UD))

print("\n=== main bundle 里 provider 连接存储相关 ===")
MAIN = r"C:\Users\yang2\AppData\Roaming\Xiaomi MiMo\runtime-res\releases\main\main~DAq2tHkd.mjs"
s = open(MAIN, "r", encoding="utf-8", errors="replace").read()
for pat in ("provider-connections", "providerConnections", "connections.json",
            "providers.json", "authorizations", "sameCredential",
            "platformUrl", "authorize/code"):
    idxs = [m.start() for m in re.finditer(re.escape(pat), s)]
    print("  %-22s x%d" % (pat, len(idxs)))
    if idxs and pat in ("provider-connections", "connections.json", "providers.json"):
        a = max(0, idxs[0] - 700)
        print("      ...%s..." % s[a:idxs[0] + 700].replace("\n", " "))
