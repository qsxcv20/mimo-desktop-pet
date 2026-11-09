#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""show_mimo.py — 找到 MiMo 的隐藏主窗口并把它显示出来。"""
import ctypes
import os
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass  # pythonw.exe 下 sys.stdout 是 None
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mimo_host as H

SW_HIDE = 0
SW_SHOWNORMAL = 1
SW_SHOW = 5
SW_RESTORE = 9

H.user32.ShowWindow.argtypes = [H.wt.HWND, ctypes.c_int]
H.user32.ShowWindow.restype = H.wt.BOOL


def find_hidden():
    out = []
    for h in H.enum_top():
        if H._cls(h) != "Chrome_WidgetWin_1":
            continue
        if not H.is_mimo_process(H._pid(h)):
            continue
        st = H._style(h)
        if not (st & H.WS_CAPTION):
            continue
        r = H._rect(h)
        if (r[2] - r[0]) < 200:
            continue
        out.append(h)
    return out


ws = find_hidden()
print("MiMo 候选窗口:", [hex(w) for w in ws])
if not ws:
    print("没有找到 MiMo 浏览器窗口")
    sys.exit(1)

hwnd = ws[0]
for h in ws:
    print(" ", hex(h), H.describe(h))

print("\n尝试 ShowWindow(SW_SHOW) ...")
H.user32.ShowWindow(hwnd, SW_SHOW)
time.sleep(0.6)
print("  IsWindowVisible =", H.user32.IsWindowVisible(hwnd))
print("  IsIconic       =", H.user32.IsIconic(hwnd))
print("  rect           =", H._rect(hwnd))

if not H.user32.IsWindowVisible(hwnd):
    print("尝试 SW_RESTORE ...")
    H.user32.ShowWindow(hwnd, SW_RESTORE)
    time.sleep(0.6)
    print("  IsWindowVisible =", H.user32.IsWindowVisible(hwnd))
    print("  rect            =", H._rect(hwnd))

if H.user32.IsWindowVisible(hwnd):
    print("\nOK 主窗口已显示 ->", hex(hwnd))
    H.force_redraw(hwnd)
else:
    print("\n仍然不可见（可能 Electron 自己 hide 了，需要走 tray 激活或 second-instance）")
