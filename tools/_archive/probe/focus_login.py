#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""focus_login.py — 把 MiMo 的「小米账号 - 登录」窗口调到前台。

用法: python focus_login.py
"""
import ctypes
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"D:\桌面宠物\pet")

import mimo_host as H

SW_RESTORE = 9
SW_SHOW = 5

KEYS = ("小米账号", "Xiaomi MiMo", "MiMo")


def main():
    found = []
    hwnd = H.user32.GetForegroundWindow()
    # 枚举所有顶层窗口
    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def cb(h, l):
        h = int(h)
        n = H.user32.GetWindowTextLengthW(h)
        if n:
            buf = ctypes.create_unicode_buffer(n + 1)
            H.user32.GetWindowTextW(h, buf, n + 1)
            t = buf.value
            if any(k in t for k in KEYS):
                found.append((h, t, bool(H.user32.IsWindowVisible(h))))
        return True

    H.user32.EnumWindows(cb, 0)

    for h, t, vis in found:
        print("hwnd=%#x visible=%s  %s" % (h, vis, t))

    # 优先「小米账号」窗口
    target = None
    for h, t, vis in found:
        if "小米账号" in t:
            target = (h, t)
            break
    if not target:
        print("没找到小米账号登录窗口")
        return 1
    h, t = target
    H.user32.ShowWindow(h, SW_SHOW)
    H.user32.ShowWindow(h, SW_RESTORE)
    H.user32.SetForegroundWindow(h)
    H.user32.BringWindowToTop(h)
    time.sleep(0.4)
    print("\n已置前:", t, hex(h))
    return 0


if __name__ == "__main__":
    sys.exit(main())
