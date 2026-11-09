#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""cdp_list.py — 列出 window.mimo 的全部方法，找登录/账号相关的入口。

用法: python cdp_list.py [关键字]
"""
import json
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"D:\桌面宠物\pet")

from mimo_cdp import MiMoCDP

KEY = (sys.argv[1] if len(sys.argv) > 1 else "").lower()


def main():
    c = MiMoCDP()
    keys = c.evaluate("window.mimo?Object.keys(window.mimo):[]") or []
    print("window.mimo 共 %d 个成员" % len(keys))
    hit = [k for k in keys if KEY in k.lower()]
    print("\n命中 %r 的: %s" % (KEY, hit if hit else "(无)"))
    print("\n全部成员:")
    for i in range(0, len(keys), 4):
        print("   " + "  ".join("%-26s" % k for k in keys[i:i + 4]))


if __name__ == "__main__":
    main()
