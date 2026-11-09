#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""hunt_cred3.py — 全盘扫描小米账号凭据落盘位置。"""
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HOME = os.path.expanduser("~")
ROOTS = [
    os.path.join(HOME, ".config", "mimocode"),
    os.path.join(HOME, ".local", "share", "mimocode"),
    os.path.join(HOME, ".mimocode"),
    os.path.join(os.environ.get("APPDATA", ""), "Xiaomi MiMo"),
    os.path.join(os.environ.get("LOCALAPPDATA", ""), "Xiaomi MiMo"),
]

TOKEN_RE = re.compile(rb"[A-Za-z0-9_\-]{28,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}")
LONG_RE = re.compile(rb'"?[A-Za-z0-9_\-]{40,}"?')


def walk(root):
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in ("Cache", "Code Cache", "GPUCache",
                                             "DawnCache", "blob_storage",
                                             "Service Worker", "Crashpad",
                                             "logs", "IndexedDB")]
        for fn in fns:
            yield os.path.join(dp, fn)


print("=== 目录清单 ===")
for r in ROOTS:
    print("\n#", r, "存在" if os.path.isdir(r) else "不存在")
    if not os.path.isdir(r):
        continue
    n = 0
    for p in walk(r):
        try:
            sz = os.path.getsize(p)
        except Exception:
            continue
        name = os.path.basename(p)
        if sz < 4000 and not name.endswith((".json", ".db")):
            continue
        print("   %-9d %s" % (sz, os.path.relpath(p, r)))
        n += 1
        if n > 60:
            print("   ...")
            break

print("\n\n=== 含 token 形状字符串的文件 ===")
for r in ROOTS:
    if not os.path.isdir(r):
        continue
    for p in walk(r):
        try:
            if os.path.getsize(p) > 40 * 1024 * 1024:
                continue
            with open(p, "rb") as f:
                data = f.read()
        except Exception:
            continue
        hits = TOKEN_RE.findall(data)
        if hits:
            print("  %s" % p)
            for h in hits[:3]:
                print("      JWT?", h[:60].decode("ascii", "replace"))
            continue
        if b"xiaomi" in data.lower() and (b"token" in data.lower() or
                                          b"access" in data.lower()):
            longs = [x for x in LONG_RE.findall(data)
                     if b"xiaomi" not in x.lower() and len(x) > 45]
            if longs:
                print("  %s" % p)
                for x in longs[:3]:
                    print("      ", x[:80].decode("ascii", "replace"))
