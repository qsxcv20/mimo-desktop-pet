#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""esc.py — 给前台窗口发 ESC（用来关掉开始菜单之类的浮层）。

用法: python esc.py
"""
import ctypes
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"D:\桌面宠物\pet")

import mimo_host as H

VK_ESCAPE = 0x1B
KEYEVENTF_KEYUP = 0x0002

fg = H.user32.GetForegroundWindow()
n = H.user32.GetWindowTextLengthW(fg)
title = ""
if n:
    buf = ctypes.create_unicode_buffer(n + 1)
    H.user32.GetWindowTextW(fg, buf, n + 1)
    title = buf.value
print("前台窗口 %#x class=%s title=%r" % (fg, H._cls(fg), title))

H.user32.keybd_event(VK_ESCAPE, 0, 0, 0)
time.sleep(0.1)
H.user32.keybd_event(VK_ESCAPE, 0, KEYEVENTF_KEYUP, 0)
time.sleep(0.8)
print("已发送 ESC")
