#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
win_probe.py — 探查 MiMo Desktop 主窗口，并测试把一个窗口 SetParent 成它的子窗口。

只读探查 + 一个最小原型验证，不改 MiMo 任何文件。
"""
import ctypes
import ctypes.wintypes as wt
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass  # pythonw.exe 下 sys.stdout 是 None

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

EnumWindowsProc = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)

TITLE_MAX = 512


def get_text(hwnd):
    buf = ctypes.create_unicode_buffer(TITLE_MAX)
    user32.GetWindowTextW(hwnd, buf, TITLE_MAX)
    return buf.value


def get_class(hwnd):
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buf, 256)
    return buf.value


def get_pid(hwnd):
    pid = wt.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value


def enum_windows():
    out = []
    def cb(hwnd, lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        t = get_text(hwnd)
        c = get_class(hwnd)
        p = get_pid(hwnd)
        out.append((hwnd, t, c, p))
        return True
    user32.EnumWindows(EnumWindowsProc(cb), 0)
    return out


def proc_name(pid):
    try:
        h = kernel32.OpenProcess(0x1000, False, pid)
        if not h:
            return None
        buf = ctypes.create_unicode_buffer(260)
        if kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(wt.DWORD(len(buf)))):
            return buf.value
        kernel32.CloseHandle(h)
    except Exception:
        pass
    return None


def main():
    print("=== 枚举可见顶层窗口（找 Xiaomi MiMo） ===")
    mimo = []
    for hwnd, title, cls, pid in enum_windows():
        name = proc_name(pid) or ""
        if "Xiaomi MiMo" in name or "MiMo" in title:
            r = wt.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(r))
            print("  hwnd=0x%X pid=%-6d cls=%-28s title=%r  rect=(%d,%d,%d,%d) size=%dx%d"
                  % (hwnd, pid, cls[:28], title[:40],
                     r.left, r.top, r.right, r.bottom, r.right - r.left, r.bottom - r.top))
            mimo.append((hwnd, title, cls, pid, r))

    print("\n=== 结论 ===")
    if not mimo:
        print("  没找到 MiMo 窗口（可能没启动或窗口标题为空）")
        return 1
    print("  找到 %d 个 MiMo 窗口。" % len(mimo))
    print("  SetParent 方案：把桌宠 HWND 的 parent 设为上面的主窗口 hwnd，")
    print("  即可让桌宠成为其原生子窗口 —— 被裁剪在客户区内、随窗口移动/最小化/关闭。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
