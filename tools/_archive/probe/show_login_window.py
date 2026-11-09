#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""show_login_window.py — 找出 MiMo 的隐藏 SSO 登录窗口并显示出来。

MiMo 的 SSO WebView 窗口创建时 show:false，登录过期时可能一直藏着，
用户看不到「请登录」的界面。这里把它找出来置前。

用法: python show_login_window.py
"""
import ctypes
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"D:\桌面宠物\pet")

import mimo_host as H

SW_SHOW = 5
SW_RESTORE = 9


def enum_windows():
    out = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def cb(h, l):
        h = int(h)
        n = H.user32.GetWindowTextLengthW(h)
        title = ""
        if n:
            buf = ctypes.create_unicode_buffer(n + 1)
            H.user32.GetWindowTextW(h, buf, n + 1)
            title = buf.value
        pid = ctypes.c_ulong()
        H.user32.GetWindowThreadProcessId(h, ctypes.byref(pid))
        cls = H._cls(h)
        out.append({"hwnd": h, "title": title, "pid": pid.value,
                    "cls": cls, "vis": bool(H.user32.IsWindowVisible(h))})
        return True

    H.user32.EnumWindows(cb, 0)
    return out


def main():
    wins = enum_windows()
    mimos = [w for w in wins if "MiMo" in w["title"] or "小米" in w["title"]
             or w["cls"] == "Chrome_WidgetWin_1"]
    print("候选窗口:")
    for w in mimos:
        print("  hwnd=%#x pid=%-6s vis=%-5s cls=%-22s %s"
              % (w["hwnd"], w["pid"], w["vis"], w["cls"], w["title"][:44]))

    hidden = [w for w in mimos if not w["vis"]
              and w["cls"] == "Chrome_WidgetWin_1"]
    if not hidden:
        print("\n没有隐藏的 MiMo 窗口")
        return 1
    for w in hidden:
        h = w["hwnd"]
        print("\n显示隐藏窗口 %s (%#x)" % (w["title"], h))
        H.user32.ShowWindow(h, SW_SHOW)
        H.user32.ShowWindow(h, SW_RESTORE)
        H.user32.SetForegroundWindow(h)
        H.user32.BringWindowToTop(h)
    time.sleep(1.0)
    print("已置前")
    return 0


if __name__ == "__main__":
    sys.exit(main())
