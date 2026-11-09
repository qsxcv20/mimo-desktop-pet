#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""scan_ls.py — 挖 Local Storage leveldb 里的键与 DPAPI blob。"""
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

LS = os.path.join(os.environ["APPDATA"], "Xiaomi MiMo", "Local Storage", "leveldb")
print("目录:", LS)
if not os.path.isdir(LS):
    sys.exit(1)

DPAPI = re.compile(rb'v1[01][A-Za-z0-9+/=]{40,}')
KEYS = re.compile(rb'[\x20-\x7e]{6,120}')

for fn in sorted(os.listdir(LS)):
    p = os.path.join(LS, fn)
    if not os.path.isfile(p):
        continue
    sz = os.path.getsize(p)
    if sz == 0:
        continue
    with open(p, "rb") as f:
        data = f.read()
    dp = DPAPI.findall(data)
    print("\n### %s (%d bytes)  DPAPI blob x%d" % (fn, sz, len(dp)))
    for d in dp[:4]:
        print("    blob:", d[:60].decode("ascii", "replace"))
    # 找看起来像 key 的可打印串
    seen = set()
    for m in KEYS.finditer(data):
        s = m.group(0)
        low = s.lower()
        if any(k.encode() in low for k in ("xiaomi", "account", "token", "auth", "user",
                                           "mimo", "sso", "login", "passport")):
            if s not in seen:
                seen.add(s)
                print("    key?", s[:120].decode("ascii", "replace"))
        if len(seen) > 14:
            break
