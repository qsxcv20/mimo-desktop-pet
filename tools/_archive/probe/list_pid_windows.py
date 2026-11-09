#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""list_pid_windows.py — 列出某个进程的所有顶层窗口（含无标题的）。

用法: python list_pid_windows.py <pid>
"""
import ctypes
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"D:\桌面宠物\pet")

import mimo_host as H


def main():
    want = int(sys.argv[1])
    rows = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def cb(h, l):
        h = int(h)
        pid = ctypes.c_ulong()
        H.user32.GetWindowThreadProcessId(h, ctypes.byref(pid))
        if pid.value != want:
            return True
        n = H.user32.GetWindowTextLengthW(h)
        title = ""
        if n:
            buf = ctypes.create_unicode_buffer(n + 1)
            H.user32.GetWindowTextW(h, buf, n + 1)
            title = buf.value
        rows.append((h, title, H._cls(h),
                     bool(H.user32.IsWindowVisible(h)), H._rect(h)))
        return True

    H.user32.EnumWindows(cb, 0)
    print("pid=%d 的顶层窗口 %d 个" % (want, len(rows)))
    for h, t, c, v, r in rows:
        print("  hwnd=%#x vis=%-5s cls=%-24s rect=%-28s title=%r"
              % (h, v, c, str(r), t[:40]))


if __name__ == "__main__":
    main()
