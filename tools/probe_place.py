#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
probe_place.py — 实测算 place_bubble 对「高贴纸气泡」的摆位结果。

用法：
    python tools/probe_place.py
"""

import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass  # pythonw.exe 下 sys.stdout 是 None

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "pet"))

import mimo_host as H                          # noqa: E402
from mimo_bubble import place_bubble          # noqa: E402


class FakeBubble(object):
    def __init__(self, w, h):
        self._w, self._h = w, h

    def width(self):
        return self._w

    def height(self):
        return self._h


def main():
    host = H.find_mimo_window(timeout=3)
    if not host:
        print("找不到 MiMo")
        return 1
    ox, oy = H.client_to_screen(host, 0, 0)
    cw, ch = H.client_size(host) if hasattr(H, "client_size") else (0, 0)
    print("MiMo client origin=(%s,%s) size=(%s,%s)" % (ox, oy, cw, ch))
    print("MiMo window rect=%s" % (H._rect(host),))

    cx, cy = 1056, 665          # 配置里的客户区坐标
    pet_size = 220
    px, py = ox + cx, oy + cy
    print("桌宠屏幕坐标=(%s,%s)" % (px, py))

    for name, (bw, bh) in (("额度气泡", (214, 172)), ("贴纸气泡", (328, 370))):
        b = FakeBubble(bw, bh)
        x, y, side, tx = place_bubble(b, px, py, pet_size, pet_size,
                                      ox, oy, cw, ch)
        print("\n%s %dx%d ->" % (name, bw, bh))
        print("  位置=(%s,%s)  尾巴=%s@%.2f" % (x, y, side, tx))
        inside = (ox <= x and oy <= y and
                  x + bw <= ox + cw and y + bh <= oy + ch)
        print("  在客户区内? %s" % ("是" if inside else "否 <-- 问题"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
