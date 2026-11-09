#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""probe_interval.py - 测真实鼠标两次点击的实际间隔。

Windows 的双击间隔阈值是 GetDoubleClickTime()（默认 500ms），
但真人双击的实际间隔通常 100~250ms。
本探针把每次点击的时刻记下来，算出真实间隔，
用来定 GESTURE_WAIT_MS（单击挂起窗口）。

用法:
    python tools/probe_interval.py
"""

import ctypes
import json
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "pet"))

import mimo_host as H                          # noqa: E402

user32 = H.user32
STATUS = os.path.join(ROOT, "pet", "pet_status.json")


def find_win(title):
    out = []
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p,
                                     ctypes.c_void_p)

    def cb(h, _l):
        if H._text(h) == title:
            out.append(int(h))
        return True

    user32.EnumWindows(WNDENUMPROC(cb), 0)
    return out[0] if out else None


def status():
    try:
        with open(STATUS, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}


def real_click(x, y):
    user32.SetCursorPos(int(x), int(y))
    time.sleep(0.02)
    user32.mouse_event(0x0002, 0, 0, 0, 0)
    time.sleep(0.03)
    user32.mouse_event(0x0004, 0, 0, 0, 0)


def main():
    # 1) 读系统的双击间隔
    dct = user32.GetDoubleClickTime()
    print("系统 GetDoubleClickTime() = %d ms" % dct)

    pet = find_win("MiMo 桌宠")
    if not pet:
        print("找不到桌宠")
        return 1
    r = H._rect(pet)
    w = r[2] - r[0]
    h = r[3] - r[1]
    cx = r[0] + int(w * 116 / 220.0)
    cy = r[1] + int(h * 59 / 220.0)

    print("")
    print("真实鼠标连点 6 次，记录每次计数的到达时刻：")
    stamps = []
    prev_clicks = (status().get("egg") or {}).get("clicks") or 0
    for i in range(6):
        t0 = time.time()
        real_click(cx, cy)
        # 等计数涨
        deadline = t0 + 1.5
        while time.time() < deadline:
            c = (status().get("egg") or {}).get("clicks") or 0
            if c > prev_clicks:
                stamps.append((t0, time.time(), c - prev_clicks))
                prev_clicks = c
                break
            time.sleep(0.005)
        time.sleep(0.12)

    for i, (t0, t1, dn) in enumerate(stamps):
        gap = ""
        if i:
            gap = " 距上次 %.0f ms" % ((t0 - stamps[i - 1][0]) * 1000)
        print("  第 %d 次: 发送 +%.0f ms 计数到账 +%.0f ms (+%d)%s"
              % (i + 1, (t1 - t0) * 1000, (t1 - t0) * 1000, dn, gap))

    return 0


if __name__ == "__main__":
    sys.exit(main())
