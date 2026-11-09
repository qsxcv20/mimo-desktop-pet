#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""probe_dbl3.py - 用**真实鼠标**测试双击，确认 Windows 的双击合成。

PostMessage 投的 WM_LBUTTONDOWN 不会触发 Windows 的双击合成
（DBLCLK 是由输入队列根据时间+位置合成的），
所以要测真实双击，必须用真实鼠标事件（mouse_event）。

桌宠是 layered window，命中测试不稳定 —— 但这里只需要
「双击事件有没有到达」，所以只要点中桌宠的实心区域即可，
点空了就重试几个候选点。

用法:
    python tools/probe_dbl3.py
"""

import ctypes
import json
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "pet"))

import mimo_host as H                          # noqa: E402

user32 = H.user32
STATUS = os.path.join(ROOT, "pet", "pet_status.json")
CMD = os.path.join(ROOT, "pet", "pet_cmd.json")

MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004


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


def lparam(x, y):
    return (y << 16) | (x & 0xFFFF)


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
    time.sleep(0.05)
    user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.04)
    user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)


def snap(tag):
    st = status()
    egg = st.get("egg") or {}
    b = find_win("MiMo 桌宠气泡")
    vis = bool(b and user32.IsWindowVisible(b))
    sz = None
    if b:
        r = H._rect(b)
        sz = (r[2] - r[0], r[3] - r[1])
    print("  %-12s clicks=%-5s sticker_mode=%-5s vis=%-5s size=%s debug=%r"
          % (tag, egg.get("clicks"), egg.get("sticker_mode"), vis, sz,
             st.get("debug")))


def main():
    pet = find_win("MiMo 桌宠")
    if not pet:
        print("找不到桌宠")
        return 1
    r = H._rect(pet)
    w = r[2] - r[0]
    h = r[3] - r[1]
    print("桌宠 hwnd=%s 窗口 %dx%d" % (hex(pet), w, h))

    send_cmd({"action": "hidebubble"})
    time.sleep(1.0)
    snap("起点")

    # 候选命中点（桌宠实心区域：脸/身体）
    cands = [(116, 59), (110, 80), (100, 70), (120, 45), (108, 95),
             (125, 60), (95, 60), (112, 110)]

    print("真实鼠标双击:")
    for (fx, fy) in cands:
        cx = r[0] + int(w * fx / 220.0)
        cy = r[1] + int(h * fy / 220.0)
        before = (status().get("egg") or {}).get("clicks") or 0
        real_click(cx, cy)
        time.sleep(0.09)
        real_click(cx, cy)
        time.sleep(1.2)
        after = (status().get("egg") or {}).get("clicks") or 0
        if after > before:
            print("  命中点 (窗口内 %d,%d -> 屏幕 %d,%d) 计数 %s->%s"
                  % (fx, fy, cx, cy, before, after))
            snap("双击后")
            break
    else:
        print("  所有候选点都没命中")
        snap("双击后")

    return 0


if __name__ == "__main__":
    sys.exit(main())
