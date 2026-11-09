#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""dump_region.py — 十六进制+ASCII dump 指定区域，找 mi.com 会话 token。"""
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

UD = os.path.join(os.environ["APPDATA"], "Xiaomi MiMo")
TARGETS = [
    (os.path.join(UD, "Local Storage", "leveldb"), [b"tokens_%", b"user_unique"]),
    (os.path.join(UD, "Partitions", "rp-browser", "Local Storage", "leveldb"),
     [b"tokens", b"user_unique", b"serviceToken", b"cUserId", b"userId"]),
]


def hexdump(data, base=0, width=32):
    out = []
    for i in range(0, len(data), width):
        chunk = data[i:i + width]
        h = " ".join("%02x" % c for c in chunk)
        a = "".join(chr(c) if 32 <= c < 127 else "." for c in chunk)
        out.append("%08x  %-*s  %s" % (base + i, width * 3, h, a))
    return "\n".join(out)


for root, pats in TARGETS:
    if not os.path.isdir(root):
        print("\n### 目录不存在:", root)
        continue
    for fn in sorted(os.listdir(root)):
        p = os.path.join(root, fn)
        if not os.path.isfile(p) or os.path.getsize(p) == 0:
            continue
        try:
            data = open(p, "rb").read()
        except Exception:
            continue
        for pat in pats:
            for m in list(re.finditer(re.escape(pat), data))[:2]:
                a = max(0, m.start() - 120)
                b = min(len(data), m.end() + 900)
                print("\n\n######## %s :: %s @%d ########" % (fn, pat.decode(), m.start()))
                print(hexdump(data[a:b], a))
