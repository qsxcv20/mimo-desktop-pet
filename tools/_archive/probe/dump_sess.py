#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""dump_sess.py — 把 Session Storage 里 mimo-server 相关条目全量 dump。"""
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = os.path.join(os.environ["APPDATA"], "Xiaomi MiMo", "Partitions",
                    "xiaomi-account", "Session Storage", "000003.log")
data = open(BASE, "rb").read()
print("size", len(data))

# 找所有 namespace 之后的一段内容
idxs = [m.start() for m in re.finditer(rb'mimo-server-cn\.xiaomimimo\.com', data)]
print("hits:", len(idxs))

# 找 key=value 形式的长串
PAT = re.compile(rb'[A-Za-z0-9_\-\.]{12,}')
seen = set()
out = []
for m in PAT.finditer(data):
    s = m.group(0)
    if s in seen:
        continue
    seen.add(s)
    # 排除明显的 session-storage 命名空间 uuid
    if re.fullmatch(rb'[0-9a-f\-]{36}', s):
        continue
    out.append(s.decode("ascii", "replace"))

print("\n=== 疑似 token / key 串 (%d) ===" % len(out))
for s in out:
    print("   ", s)

print("\n=== 可打印片段 >= 10 ===")
for s in re.findall(rb'[\x20-\x7e]{10,300}', data):
    t = s.decode("ascii", "replace")
    if "namespace" in t:
        continue
    print("   ", t[:280])
