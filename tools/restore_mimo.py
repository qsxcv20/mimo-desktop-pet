#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""restore_mimo.py — 把最小化的 MiMo 主窗口恢复到正常状态，并做渲染层健康检查。

背景：
    MiMo 偶发被最小化到哨兵坐标 (-32000,-32000,-31840,-31972)，
    此时 GetWindowRect 返回 160x28 的假矩形，桌宠也会跟着隐藏。
    这个脚本只做 SW_RESTORE（等同用户点任务栏图标），不碰尺寸，
    避免重演"改尺寸把 Chromium 渲染层搞挂"的事故。

用法: python restore_mimo.py
"""
import os
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass  # pythonw.exe 下 sys.stdout 是 None
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pet"))

import mimo_host as H  # noqa: E402
import grab_window as G  # noqa: E402

SW_RESTORE = 9
SW_SHOW = 5


def render_health(hwnd):
    """抓一次窗口算非背景像素占比，判定渲染层是否还活着。"""
    r = H._rect(hwnd)
    w, h = r[2] - r[0], r[3] - r[1]
    if w < 200 or h < 200:
        return None, 0.0
    im, ok = G.grab(hwnd)
    im.convert("RGB").save(r"D:\桌面宠物\_mimo\mimo-printwindow.png")
    from PIL import Image
    base = Image.new("RGB", im.size, (30, 30, 30))
    import numpy as np
    a = np.asarray(im.convert("RGB"), dtype=np.int16)
    b = np.asarray(base, dtype=np.int16)
    same = (np.abs(a - b).max(axis=2) <= 6)
    ratio = 1.0 - float(same.mean())
    return im, ratio


def main():
    hwnd = H.find_mimo_window(timeout=10, include_hidden=True)
    if not hwnd:
        print("找不到 MiMo 窗口")
        return 1
    print("MiMo hwnd=0x%x  iconic=%s  rect=%s"
          % (hwnd, H.is_minimized(hwnd), H._rect(hwnd)))

    if H.is_minimized(hwnd):
        H.user32.ShowWindow(hwnd, SW_RESTORE)
        for _ in range(30):
            time.sleep(0.2)
            if not H.is_minimized(hwnd):
                break
        H.user32.SetForegroundWindow(hwnd)
        time.sleep(1.2)

    print("恢复后 iconic=%s  rect=%s  client=%s"
          % (H.is_minimized(hwnd), H._rect(hwnd), H.client_size(hwnd)))

    im, ratio = render_health(hwnd)
    if im is None:
        print("渲染层检查: 窗口尺寸异常")
        return 2
    print("渲染层检查: %dx%d  非背景像素 %.2f%%  -> %s"
          % (im.width, im.height, ratio * 100,
             "OK" if ratio > 0.3 else "黑屏！需要 restart_mimo.py"))

    # 桌宠是否重新出现
    time.sleep(1.5)
    st = r"D:\桌面宠物\pet\pet_status.json"
    if os.path.exists(st):
        import json
        with open(st, "r", encoding="utf-8", errors="replace") as f:
            print("桌宠状态:", json.load(f))
    return 0


if __name__ == "__main__":
    sys.exit(main())
