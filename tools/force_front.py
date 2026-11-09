#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""force_front.py — 强制把某个窗口提到最前（topmost 技巧）。

用法: python force_front.py <hwnd>
"""
import ctypes
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass  # pythonw.exe 下 sys.stdout 是 None
sys.path.insert(0, r"D:\桌面宠物\pet")

import mimo_host as H

HWND_TOPMOST = -1
HWND_NOTOPMOST = -2
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_SHOWWINDOW = 0x0040


def main():
    hwnd = int(sys.argv[1], 0)
    H.user32.ShowWindow(hwnd, 5)
    H.user32.ShowWindow(hwnd, 9)
    H.user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                           SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
    time.sleep(0.3)
    H.user32.SetForegroundWindow(hwnd)
    H.user32.BringWindowToTop(hwnd)
    time.sleep(1.2)
    H.user32.SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0,
                           SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
    print("已置前 hwnd=%#x  rect=%s" % (hwnd, H._rect(hwnd)))


if __name__ == "__main__":
    main()
