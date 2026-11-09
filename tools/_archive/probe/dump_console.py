#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""dump_console.py — 打印开放平台 JS 的指定字符区间。

用法: python dump_console.py <start> <len>
"""
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
JS = r"D:\桌面宠物\_mimo\console\main.dd4c96b8f4cc7ba6.chunk.js"

start = int(sys.argv[1]) if len(sys.argv) > 1 else 445000
ln = int(sys.argv[2]) if len(sys.argv) > 2 else 4000

d = open(JS, "r", encoding="utf-8", errors="replace").read()
print("total=%d\n" % len(d))
print(d[start:start + ln].replace("\n", " "))
