#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""probe_dbl5.py - 真实鼠标双击（先把 MiMo 置前，避免被别的窗口抢焦点）。

真实鼠标会打到「屏幕上最上面的那个窗口」。如果别的应用
（比如同时开着的浏览器）盖在 MiMo 上面，点击就落在它身上，
桌宠根本收不到 —— 这是之前踩过的坑。
所以先把 MiMo 提到最前再点。

用法:
    python tools/probe_dbl5.py
"""

import ctypes
import json
import os
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass  # pythonw.exe 下 sys.stdout 是 None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "pet"))

import mimo_host as H                          # noqa: E402

user32 = H.user32
STATUS = os.path.join(ROOT, "pet", "pet_status.json")
CMD = os.path.join(ROOT, "pet", "pet_cmd.json")

HWND_TOPMOST = -1
HWND_NOTOPMOST = -2
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_SHOWWINDOW = 0x0040


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


def bring_to_front(hwnd):
    user32.ShowWindow(hwnd, 5)
    user32.ShowWindow(hwnd, 9)
    user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                        SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
    time.sleep(0.3)
    user32.SetForegroundWindow(hwnd)
    user32.BringWindowToTop(hwnd)
    time.sleep(0.5)
    user32.SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0,
                        SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)


def status():
    try:
        with open(STATUS, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}


def send_cmd(payload):
    payload["ts"] = int(time.time() * 1000)
    tmp = CMD + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    os.replace(tmp, CMD)


def real_click(x, y):
    user32.SetCursorPos(int(x), int(y))
    time.sleep(0.06)
    user32.mouse_event(0x0002, 0, 0, 0, 0)
    time.sleep(0.04)
    user32.mouse_event(0x0004, 0, 0, 0, 0)


def snap(tag):
    st = status()
    egg = st.get("egg") or {}
    b = find_win("MiMo 桌宠气泡")
    vis = bool(b and user32.IsWindowVisible(b))
    sz = None
    if b:
        r = H._rect(b)
        sz = (r[2] - r[0], r[3] - r[1])
    print("  %-12s clicks=%-5s sticker_mode=%-5s vis=%-5s size=%s"
          % (tag, egg.get("clicks"), egg.get("sticker_mode"), vis, sz))


def main():
    pet = find_win("MiMo 桌宠")
    mimo = H.find_mimo_window(timeout=8, include_hidden=True)
    if not pet:
        print("找不到桌宠")
        return 1
    print("桌宠=%s MiMo=%s" % (hex(pet), hex(mimo) if mimo else None))

    send_cmd({"action": "hidebubble"})
    time.sleep(1.0)
    snap("起点")

    if mimo:
        bring_to_front(mimo)
        time.sleep(0.8)

    pet = find_win("MiMo 桌宠")
    r = H._rect(pet)
    w = r[2] - r[0]
    h = r[3] - r[1]
    cands = [(116, 59), (110, 80), (100, 70), (120, 45), (108, 95),
             (125, 60), (95, 60), (112, 110), (100, 55), (118, 75)]

    for (fx, fy) in cands:
        cx = r[0] + int(w * fx / 220.0)
        cy = r[1] + int(h * fy / 220.0)
        before = (status().get("egg") or {}).get("clicks") or 0
        real_click(cx, cy)
        time.sleep(0.09)
        real_click(cx, cy)
        time.sleep(1.4)
        after = (status().get("egg") or {}).get("clicks") or 0
        if after > before:
            print("  命中 (窗口内 %d,%d -> 屏幕 %d,%d) 计数 %s->%s"
                  % (fx, fy, cx, cy, before, after))
            snap("双击后")
            return 0
    print("  所有候选点都没命中（桌宠可能不在前台）")
    snap("双击后")
    return 1


if __name__ == "__main__":
    sys.exit(main())
