#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""restart_mimo.py — 优雅重启 MiMo Desktop，并在启动后验证渲染层是否正常。

用法:
    python restart_mimo.py          # 重启
    python restart_mimo.py --check  # 只检查当前窗口渲染
"""
import os
import subprocess
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass  # pythonw.exe 下 sys.stdout 是 None
sys.path.insert(0, r"D:\桌面宠物\pet")
sys.path.insert(0, r"D:\桌面宠物\tools")

import mimo_host as H

EXE = r"C:\Users\yang2\AppData\Local\Programs\Xiaomi MiMo\Xiaomi MiMo.exe"
WM_CLOSE = 0x0010

import ctypes
from ctypes import wintypes as wt
H.user32.PostMessageW.argtypes = [wt.HWND, ctypes.c_uint, ctypes.c_ulonglong,
                                   ctypes.c_longlong]
H.user32.PostMessageW.restype = wt.BOOL


def close_mimo():
    host = H.find_mimo_window(timeout=3, include_hidden=True)
    if host:
        H.user32.PostMessageW(host, WM_CLOSE, 0, 0)
        print("已发送 WM_CLOSE ->", hex(host))
    for _ in range(30):
        time.sleep(0.5)
        if not H.find_mimo_window(timeout=0, include_hidden=True):
            break
    # 还活着就强杀
    out = subprocess.run(["taskkill", "/IM", "Xiaomi MiMo.exe", "/F"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.5)


def start_mimo(port=None):
    args = [EXE, "--updated"]
    if port:
        args.append("--remote-debugging-port=%d" % int(port))
    subprocess.Popen(args,
                     creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
    print("已启动 MiMo%s，等待主窗口…"
          % ("（调试端口 %s）" % port if port else ""))
    host = H.find_mimo_window(timeout=60, include_hidden=True)
    if not host:
        print("!! 60 秒内没找到主窗口")
        return None
    H.user32.ShowWindow(host, 5)
    time.sleep(4.0)
    return host


def check(host):
    """用 PrintWindow 抓内容，判断渲染层是否活着。"""
    from grab_window import grab
    im, ok = grab(host)
    rgb = im.convert("RGB")
    w, h = rgb.size
    px = list(rgb.getdata())
    # 统计「非背景色」像素占比：MiMo 深色主题背景约 (30,30,30)
    bg = sum(1 for p in px if abs(p[0] - 30) < 6 and abs(p[1] - 30) < 6
             and abs(p[2] - 30) < 6)
    content = 100.0 * (len(px) - bg) / len(px)
    out = r"D:\桌面宠物\_mimo\mimo-render-check.png"
    rgb.save(out)
    print("PrintWindow ok=%s  %dx%d  非背景像素 %.2f%%  -> %s"
          % (ok, w, h, content, out))
    if content < 0.5:
        print("   ★ 渲染层仍然是空的（黑屏）")
        return False
    print("   ✓ 渲染层正常")
    return True


if __name__ == "__main__":
    if "--check" in sys.argv:
        host = H.find_mimo_window(timeout=6, include_hidden=True)
        if not host:
            print("找不到 MiMo 窗口")
            sys.exit(1)
        sys.exit(0 if check(host) else 1)
    print("== 重启 MiMo ==")
    close_mimo()
    port = None
    for i, a in enumerate(sys.argv):
        if a == "--port" and i + 1 < len(sys.argv):
            port = int(sys.argv[i + 1])
    host = start_mimo(port)
    if not host:
        sys.exit(1)
    print("主窗口:", hex(host), H.describe(host))
    sys.exit(0 if check(host) else 1)
