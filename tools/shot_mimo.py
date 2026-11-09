#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""shot_mimo.py — 截 MiMo 窗口区域，用于验证桌宠是否真的在窗口里面。

用法:
    python shot_mimo.py              截图（自动弹气泡）
    python shot_mimo.py --nobubble   不弹气泡
"""
import os
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass  # pythonw.exe 下 sys.stdout 是 None
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, r"D:\桌面宠物\pet")

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QGuiApplication

import mimo_host as H

OUT_DIR = r"D:\桌面宠物\_mimo"


def find_pet_windows():
    import ctypes
    from ctypes import wintypes
    out = []
    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def cb(h, _l):
        if H._text(h) in ("MiMo 桌宠", "MiMo 桌宠气泡"):
            out.append((H._text(h), h))
        return True

    H.user32.EnumWindows(WNDENUMPROC(cb), 0)
    return out


def main():
    app = QApplication(sys.argv)
    hwnd = H.find_mimo_window(timeout=8, include_hidden=True)
    if not hwnd:
        print("!! 找不到 MiMo 窗口")
        return 1

    info = H.describe(hwnd)
    print("MiMo 主窗口 :", hex(hwnd), info["rect"], "client=%s" % (info["client"],))

    # 把 MiMo 提到前台，保证 owned window（桌宠/气泡）在最上层
    H.user32.ShowWindow(hwnd, 5)              # SW_SHOW
    H.user32.SetForegroundWindow(hwnd)
    H.user32.BringWindowToTop(hwnd)
    time.sleep(0.6)

    # 默认让桌宠弹一次气泡。
    # --keep 表示保留桌宠当前已有的气泡（比如彩蛋贴纸气泡），
    # 不要用额度气泡把它覆盖掉。
    if "--nobubble" not in sys.argv and "--keep" not in sys.argv:
        # 让桌宠弹一次气泡
        cmd_file = r"D:\桌面宠物\pet\pet_cmd.json"
        import json
        with open(cmd_file, "w", encoding="utf-8") as f:
            json.dump({"action": "bubble", "ts": int(time.time() * 1000)}, f)
        time.sleep(2.2)
    else:
        time.sleep(0.4)

    wins = find_pet_windows()
    for title, h in wins:
        owner = H.user32.GetWindowLongPtrW(h, H.GWLP_HWNDPARENT) or 0
        print("  %-14s hwnd=%-12s rect=%s owner=%s visible=%s"
              % (title, hex(h), H._rect(h), hex(owner),
                 H.user32.IsWindowVisible(h)))

    shot = QGuiApplication.primaryScreen().grabWindow(0)
    r = H._rect(hwnd)
    img = shot.copy(r[0], r[1], r[2] - r[0], r[3] - r[1])
    out = os.path.join(OUT_DIR, "in-window.png")
    img.save(out)
    print("整窗截图 -> %s (%dx%d)" % (out, img.width(), img.height()))

    # 桌宠特写（包含气泡）
    pet_rects = [H._rect(h) for t, h in wins if t == "MiMo 桌宠"]
    bub_rects = [H._rect(h) for t, h in wins if t == "MiMo 桌宠气泡"]
    if pet_rects:
        pr = pet_rects[0]
        x0 = min([pr[0]] + [b[0] for b in bub_rects])
        y0 = min([pr[1]] + [b[1] for b in bub_rects])
        x1 = max([pr[2]] + [b[2] for b in bub_rects])
        y1 = max([pr[3]] + [b[3] for b in bub_rects])
        pad = 14
        x0 = max(r[0], x0 - pad); y0 = max(r[1], y0 - pad)
        x1 = min(r[2], x1 + pad); y1 = min(r[3], y1 + pad)
        detail = shot.copy(x0, y0, x1 - x0, y1 - y0)
        out2 = os.path.join(OUT_DIR, "pet-detail.png")
        detail.save(out2)
        print("桌宠特写 -> %s (%dx%d)" % (out2, detail.width(), detail.height()))

        inside = (r[0] <= pr[0] and r[1] <= pr[1] and pr[2] <= r[2] and pr[3] <= r[3])
        print("桌宠 rect=%s  MiMo rect=%s  -> %s"
              % (pr, r, "在窗口内 ✓" if inside else "超出窗口 ✗"))
        owner = H.user32.GetWindowLongPtrW(wins[0][1], H.GWLP_HWNDPARENT) or 0
        print("owner 指针 : %s (MiMo=%s) -> %s"
              % (hex(owner), hex(hwnd),
                 "绑定成功 ✓" if owner == hwnd else "未绑定 ✗"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
