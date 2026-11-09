#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""xiaomi_login.py — 通过 CDP 触发 MiMo 的小米账号登录，并把登录窗口置前。

用法: python xiaomi_login.py
"""
import ctypes
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"D:\桌面宠物\pet")

import mimo_host as H
from mimo_cdp import MiMoCDP

SW_SHOW = 5
SW_RESTORE = 9


def enum_mimo_windows():
    out = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def cb(h, l):
        h = int(h)
        pid = ctypes.c_ulong()
        H.user32.GetWindowThreadProcessId(h, ctypes.byref(pid))
        n = H.user32.GetWindowTextLengthW(h)
        title = ""
        if n:
            buf = ctypes.create_unicode_buffer(n + 1)
            H.user32.GetWindowTextW(h, buf, n + 1)
            title = buf.value
        out.append({"hwnd": h, "pid": pid.value, "title": title,
                    "cls": H._cls(h),
                    "vis": bool(H.user32.IsWindowVisible(h)),
                    "rect": H._rect(h)})
        return True

    H.user32.EnumWindows(cb, 0)
    return out


def main():
    c = MiMoCDP()
    if not c.available():
        print("MiMo 没有开调试端口，无法触发登录")
        return 1
    before = {w["hwnd"] for w in enum_mimo_windows()}
    print("调用 xiaomiLoginStart() …")
    v = c.evaluate("(async()=>{try{return await window.mimo.xiaomiLoginStart()}"
                   "catch(e){return {err:String(e)}}})()")
    print("返回:", v)
    time.sleep(2.5)

    wins = enum_mimo_windows()
    new = [w for w in wins if w["hwnd"] not in before]
    print("\n新出现的窗口:")
    for w in new:
        print("  hwnd=%#x pid=%-6s vis=%-5s cls=%-20s %s"
              % (w["hwnd"], w["pid"], w["vis"], w["cls"], w["title"][:40]))

    hidden = [w for w in new if not w["vis"]]
    vis_new = [w for w in new if w["vis"]]
    for w in hidden:
        H.user32.ShowWindow(w["hwnd"], SW_SHOW)
        H.user32.ShowWindow(w["hwnd"], SW_RESTORE)
        print("  -> 已显示隐藏窗口 %#x" % w["hwnd"])
    for w in (vis_new + hidden):
        H.user32.SetForegroundWindow(w["hwnd"])
        H.user32.BringWindowToTop(w["hwnd"])
    time.sleep(1.2)

    print("\n当前 MiMo 相关窗口:")
    for w in enum_mimo_windows():
        if "MiMo" in w["title"] or "小米" in w["title"]:
            print("  hwnd=%#x pid=%-6s vis=%-5s %s"
                  % (w["hwnd"], w["pid"], w["vis"], w["title"][:44]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
