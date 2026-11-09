#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""probe_pet_windows.py — 打印桌宠 / 气泡窗口与 MiMo 主窗口的相对关系。"""
import ctypes
import os
import sys
from ctypes import wintypes

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"D:\桌面宠物\pet")
import mimo_host as H

out = []
WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)


def cb(h, _l):
    if H._text(h) in ("MiMo 桌宠", "MiMo 桌宠气泡"):
        out.append((H._text(h), h))
    return True


H.user32.EnumWindows(WNDENUMPROC(cb), 0)
for t, h in out:
    print("%-14s hwnd=%-11s rect=%-30s owner=%-11s vis=%s"
          % (t, hex(h), H._rect(h),
             hex(H.user32.GetWindowLongPtrW(h, H.GWLP_HWNDPARENT) or 0),
             H.user32.IsWindowVisible(h)))

host = H.find_mimo_window(timeout=5, include_hidden=True)
if host:
    ox, oy = H.client_to_screen(host, 0, 0)
    print("MiMo host=%s rect=%s client=%s 原点=(%d,%d)"
          % (hex(host), H._rect(host), H.client_size(host), ox, oy))
    for t, h in out:
        if t == "MiMo 桌宠":
            pr = H._rect(h)
            print("  桌宠相对客户区 = (%d, %d)"
                  % (pr[0] - ox, pr[1] - oy))
else:
    print("MiMo host = None")
