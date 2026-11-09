#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""probe_style.py - 查桌宠窗口的 **class style**，看 CS_DBLCLKS 有没有补上。

坑：CS_DBLCLKS 是 **class style**（GCL_STYLE = -26），
不是 window style（GWL_STYLE = -16）。
上一版探针读错了字段，一直显示 False，误导了排查。

用法:
    python tools/probe_style.py
"""

import ctypes
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass  # pythonw.exe 下 sys.stdout 是 None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "pet"))

import mimo_host as H                          # noqa: E402

user32 = H.user32

GWL_STYLE = -16
GWL_EXSTYLE = -20
GCL_STYLE = -26
CS_DBLCLKS = 0x0008
WS_EX_LAYERED = 0x00080000
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOOLWINDOW = 0x00000080


def find_win(title):
    out = []
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p,
                                     ctypes.c_void_p)

    def cb(h, _l):
        if H._text(h) == title:
            out.append(int(h))
        return True

    user32.EnumWindows(WNDENUMPROC(cb), 0)
    return out[0] if out else None


def cls_of(hwnd):
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buf, 256)
    return buf.value


def dump(title):
    h = find_win(title)
    if not h:
        print("%s: 找不到" % title)
        return None
    user32.GetClassLongPtrW.restype = ctypes.c_long
    user32.GetWindowLongPtrW.restype = ctypes.c_long
    style = user32.GetWindowLongPtrW(h, GWL_STYLE) & 0xFFFFFFFF
    ex = user32.GetWindowLongPtrW(h, GWL_EXSTYLE) & 0xFFFFFFFF
    cstyle = user32.GetClassLongPtrW(h, GCL_STYLE) & 0xFFFFFFFF
    print("%s" % title)
    print("   hwnd=%s class=%s" % (hex(h), cls_of(h)))
    print("   window style=0x%08X  ex=0x%08X" % (style, ex))
    print("   CLASS  style=0x%08X  -> CS_DBLCLKS = %s"
          % (cstyle, bool(cstyle & CS_DBLCLKS)))
    print("   WS_EX_LAYERED=%s WS_EX_NOACTIVATE=%s WS_EX_TOOLWINDOW=%s"
          % (bool(ex & WS_EX_LAYERED), bool(ex & WS_EX_NOACTIVATE),
             bool(ex & WS_EX_TOOLWINDOW)))
    return h


def main():
    print("=== 桌宠窗口 ===")
    dump("MiMo 桌宠")
    print("")
    print("=== 气泡窗口 ===")
    dump("MiMo 桌宠气泡")
    print("")
    print("=== MiMo 主窗口 ===")
    dump("Xiaomi MiMo")
    return 0


if __name__ == "__main__":
    sys.exit(main())
