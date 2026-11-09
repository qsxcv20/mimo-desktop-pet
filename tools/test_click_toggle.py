#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""test_click_toggle.py — 实机模拟「点桌宠」的气泡开合切换。

用户反馈：「点击之后显示的那个东西，点一下就消失了，不会给你一直显示那个东西。」
期望行为：
    第一次点 -> 气泡弹出并**常驻**
    第二次点 -> 气泡收起
    第三次点 -> 气泡再次弹出并常驻

用 Win32 mouse_event 做真实点击（先记下鼠标位置，测完还原）。
"""
import ctypes
import json
import os
import sys
import time
from ctypes import wintypes

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass  # pythonw.exe 下 sys.stdout 是 None
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pet"))

import mimo_host as H  # noqa: E402

user32 = H.user32
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
FAILS = []


def find_win(title):
    out = []
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def cb(h, _l):
        if H._text(h) == title:
            out.append(int(h))
        return True

    user32.EnumWindows(WNDENUMPROC(cb), 0)
    return out[0] if out else None


def check(name, cond, extra=""):
    print("  [%s] %s %s" % ("PASS" if cond else "FAIL", name, extra))
    if not cond:
        FAILS.append(name)


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


def click(x, y):
    user32.SetCursorPos(int(x), int(y))
    time.sleep(0.25)
    user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.06)
    user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    time.sleep(0.9)


def click_pet():
    """每次点击前重新取桌宠位置（桌宠会自己溜达，固定坐标会打空）。"""
    pet = find_win("MiMo 桌宠")
    if not pet:
        return None
    r = H._rect(pet)
    cx, cy = (r[0] + r[2]) // 2, (r[1] + r[3]) // 2
    click(cx, cy)
    return (cx, cy)


def main():
    mimo = H.find_mimo_window(timeout=8, include_hidden=True)
    pet = find_win("MiMo 桌宠")
    if not pet:
        print("找不到桌宠窗口")
        return 1
    r = H._rect(pet)
    print("MiMo=%s 桌宠=%s rect=%s" % (hex(mimo), hex(pet), r))

    old = POINT()
    user32.GetCursorPos(ctypes.byref(old))

    bub = find_win("MiMo 桌宠气泡")
    if bub and user32.IsWindowVisible(bub):
        print("先收掉已有气泡")
        click_pet()

    try:
        print("\n== 第 1 次点击 ==")
        p = click_pet()
        print("   点击于 %s" % (p,))
        bub = find_win("MiMo 桌宠气泡")
        vis1 = bool(bub and user32.IsWindowVisible(bub))
        check("第 1 次点击 -> 气泡弹出", vis1)

        print("\n== 等 11 秒（超过旧版 9 秒自动消失）==")
        time.sleep(11)
        bub = find_win("MiMo 桌宠气泡")
        vis2 = bool(bub and user32.IsWindowVisible(bub))
        check("11 秒后仍可见（常驻）", vis2)

        print("\n== 第 2 次点击（应收起）==")
        p = click_pet()
        print("   点击于 %s" % (p,))
        bub = find_win("MiMo 桌宠气泡")
        vis3 = bool(bub and user32.IsWindowVisible(bub))
        check("第 2 次点击 -> 气泡收起", not vis3)

        print("\n== 第 3 次点击（应重新弹出并常驻）==")
        p = click_pet()
        print("   点击于 %s" % (p,))
        bub = find_win("MiMo 桌宠气泡")
        vis4 = bool(bub and user32.IsWindowVisible(bub))
        check("第 3 次点击 -> 重新弹出", vis4)
        time.sleep(6)
        bub = find_win("MiMo 桌宠气泡")
        vis5 = bool(bub and user32.IsWindowVisible(bub))
        check("再等 6 秒仍可见（常驻）", vis5)
    finally:
        user32.SetCursorPos(old.x, old.y)
        print("\n鼠标位置已还原 -> (%d,%d)" % (old.x, old.y))

    print("\n结果: %s" % ("全部通过" if not FAILS else "失败 -> %s" % FAILS))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
