#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""dump_module.py — 从 webpack chunk 里抽出指定模块的源码。

用法: python dump_module.py <module_id> [max_chars]
"""
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
JS = r"D:\桌面宠物\_mimo\console\main.dd4c96b8f4cc7ba6.chunk.js"

mid = sys.argv[1]
mx = int(sys.argv[2]) if len(sys.argv) > 2 else 3000

d = open(JS, "r", encoding="utf-8", errors="replace").read()
pat = re.compile(r"(?<![0-9A-Za-z_$])" + re.escape(mid) + r":\s*(function|\(function)")
m = pat.search(d)
if not m:
    print("模块 %s 不在本 chunk 里" % mid)
    sys.exit(1)
i = m.start()
print("=== module %s @%d ===" % (mid, i))
print(d[i:i + mx].replace("\n", " "))
