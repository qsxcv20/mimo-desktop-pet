#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""scan_xacct.py — 读 xiaomi-account 分区的 Local Storage / Session Storage。"""
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = os.path.join(os.environ["APPDATA"], "Xiaomi MiMo", "Partitions",
                    "xiaomi-account")
TOK = re.compile(rb'[A-Za-z0-9_\-\.]{24,}')

for sub in ("Local Storage\\leveldb", "Session Storage"):
    d = os.path.join(BASE, sub)
    print("\n############ %s ############" % sub)
    if not os.path.isdir(d):
        print("  不存在")
        continue
    for fn in sorted(os.listdir(d)):
        p = os.path.join(d, fn)
        if not os.path.isfile(p) or os.path.getsize(p) == 0:
            continue
        try:
            data = open(p, "rb").read()
        except Exception as e:
            print("\n### %s -> 读失败 %s" % (fn, e))
            continue
        print("\n### %s (%d bytes)" % (fn, len(data)))
        # 可打印片段
        segs = re.findall(rb'[\x20-\x7e]{6,200}', data)
        seen = set()
        for s in segs:
            t = s.decode("ascii", "replace")
            if t in seen:
                continue
            seen.add(t)
            low = t.lower()
            if any(k in low for k in ("token", "uid", "account", "xiaomi", "mi.com",
                                      "userid", "session", "passport", "cookie")):
                print("   *", t[:190])
        # 长随机串（疑似 token）
        longs = [m.group(0) for m in TOK.finditer(data)
                 if len(m.group(0)) >= 28 and not m.group(0).startswith(b"http")]
        for l in longs[:12]:
            print("   ?", l.decode("ascii", "replace")[:120])
