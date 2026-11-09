#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""show_sso.py — 把 MiMo 的小米账号 SSO 登录窗口显示出来并置顶。

MiMo 的 SSO WebView 窗口是 show:false 创建的，登录过期时一直藏着，
用户根本看不到「请登录」。这里把它找出来、显示、置顶。

用法: python show_sso.py
"""
import ctypes
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"D:\桌面宠物\pet")

import mimo_host as H

SW_SHOW = 5
SW_RESTORE = 9


def mimo_pid():
    host = H.find_mimo_window(timeout=3, include_hidden=True)
    if not host:
        return None
    pid = ctypes.c_ulong()
    H.user32.GetWindowThreadProcessId(host, ctypes.byref(pid))
    return pid.value


def windows_of(pid):
    rows = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def cb(h, l):
        h = int(h)
        p = ctypes.c_ulong()
        H.user32.GetWindowThreadProcessId(h, ctypes.byref(p))
        if p.value != pid:
            return True
        n = H.user32.GetWindowTextLengthW(h)
        title = ""
        if n:
            buf = ctypes.create_unicode_buffer(n + 1)
            H.user32.GetWindowTextW(h, buf, n + 1)
            title = buf.value
        rows.append({"hwnd": h, "title": title, "cls": H._cls(h),
                     "vis": bool(H.user32.IsWindowVisible(h)),
                     "rect": H._rect(h)})
        return True

    H.user32.EnumWindows(cb, 0)
    return rows


def main():
    pid = mimo_pid()
    if not pid:
        print("找不到 MiMo 进程")
        return 1
    rows = windows_of(pid)
    print("MiMo pid=%d 窗口 %d 个" % (pid, len(rows)))
    for w in rows:
        print("  hwnd=%#x vis=%-5s cls=%-24s rect=%-26s %r"
              % (w["hwnd"], w["vis"], w["cls"], str(w["rect"]), w["title"][:30]))

    # 1) 主窗口若最小化先还原
    host = H.find_mimo_window(timeout=1, include_hidden=True)
    if host and H.user32.IsIconic(host):
        print("\n主窗口最小化了，先还原")
        H.user32.ShowWindow(host, SW_RESTORE)
        time.sleep(0.8)

    # 2) 找隐藏的 SSO WebView 窗口（Chrome_WidgetWin_0 且非 0 尺寸）
    sso = [w for w in rows
           if w["cls"] == "Chrome_WidgetWin_0"
           and (w["rect"][2] - w["rect"][0]) > 100
           and not w["vis"]]
    if not sso:
        print("\n没有隐藏的 SSO 窗口（可能已经登录过了）")
        return 0
    w = sso[0]
    print("\n显示 SSO 登录窗口 %#x rect=%s" % (w["hwnd"], w["rect"]))
    H.user32.ShowWindow(w["hwnd"], SW_SHOW)
    H.user32.ShowWindow(w["hwnd"], SW_RESTORE)
    H.user32.BringWindowToTop(w["hwnd"])
    H.user32.SetForegroundWindow(w["hwnd"])
    time.sleep(1.0)
    print("已置前")
    return 0


if __name__ == "__main__":
    sys.exit(main())
