#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""One-shot runtime probe: MiMo window state + pet window state."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pet"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import mimo_host  # noqa: E402

h = mimo_host.find_mimo_window()
if not h:
    print("MiMo window: NOT FOUND")
    raise SystemExit(0)

print("MiMo hwnd=0x%x" % h)
try:
    import win32gui, win32process
    print("  rect      =", win32gui.GetWindowRect(h))
    print("  visible   =", win32gui.IsWindowVisible(h))
    print("  iconic    =", win32gui.IsIconic(h))
    print("  placement =", win32gui.GetWindowPlacement(h))
    print("  title     =", win32gui.GetWindowText(h))
    print("  pid       =", win32process.GetWindowThreadProcessId(h)[1])
    print("  class     =", win32gui.GetClassName(h))
except Exception as e:
    print("  pywin32 err:", e)

# enumerate every MiMo window
import win32gui


def cb(hwnd, _):
    try:
        cls = win32gui.GetClassName(hwnd)
        ttl = win32gui.GetWindowText(hwnd)
    except Exception:
        return
    if "Chrome_WidgetWin" in cls or "MiMo" in ttl:
        print("  [%s] hwnd=0x%x rect=%s vis=%s iconic=%s ttl=%r"
              % (cls, hwnd, win32gui.GetWindowRect(hwnd),
                 win32gui.IsWindowVisible(hwnd), win32gui.IsIconic(hwnd), ttl[:40]))


print("\nall Chrome_WidgetWin windows:")
win32gui.EnumWindows(cb, None)
