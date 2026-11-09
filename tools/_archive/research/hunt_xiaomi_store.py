#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""hunt_xiaomi_store.py — 找含 xiaomi 账号状态的小文件。"""
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOTS = [
    os.path.join(os.environ["APPDATA"], "Xiaomi MiMo"),
    os.path.join(os.path.expanduser("~"), ".config", "mimocode"),
    os.path.join(os.path.expanduser("~"), ".local", "share", "mimocode"),
]
SKIP = {"runtime-res", "resources", "engine-config", "runtimes", "Cache",
        "Code Cache", "GPUCache", "DawnCache", "blob_storage",
        "Service Worker", "Crashpad", "logs", "git-version-store", "node_modules",
        "builtin_skills", "db", "agent"}

KW = re.compile(rb'xiaomi', re.I)


def walk(root):
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in SKIP]
        for fn in fns:
            yield os.path.join(dp, fn)


hits = []
for root in ROOTS:
    if not os.path.isdir(root):
        continue
    for p in walk(root):
        try:
            sz = os.path.getsize(p)
        except Exception:
            continue
        if sz > 8 * 1024 * 1024:
            continue
        try:
            with open(p, "rb") as f:
                data = f.read()
        except Exception:
            continue
        if not KW.search(data):
            continue
        rel = os.path.relpath(p, root)
        hits.append((sz, rel, p))
        print("\n### %s  (%d bytes)  <- %s" % (rel, sz, root))
        for m in list(KW.finditer(data))[:4]:
            a = max(0, m.start() - 160)
            b = min(len(data), m.end() + 260)
            seg = data[a:b].decode("utf-8", "replace").replace("\n", " ")
            print("    ...%s..." % seg[:400])

print("\n\n命中:", len(hits))
