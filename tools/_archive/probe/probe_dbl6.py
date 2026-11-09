#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""probe_dbl6.py - 确认 on_double_click 有没有被调用。

用 PostMessage 发两次「按下+松开」，然后分时采样：
  egg.clicks     -> release 计数（应该在 +2）
  sticker_mode   -> on_double_click 里会立刻占位成 sticker
  debug          -> show_sticker 里的诊断
  气泡尺寸        -> 贴纸应该是 228x270
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
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
CMD = os.path.join(ROOT, "pet", "pet_cmd.json")
STATUS = os.path.join(ROOT, "pet", "pet_status.json")


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


def send_cmd(payload):
    payload["ts"] = int(time.time() * 1000)
    tmp = CMD + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    os.replace(tmp, CMD)


def snap(tag):
    b = find_win("MiMo 桌宠气泡")
    vis = bool(b and user32.IsWindowVisible(b))
    sz = None
    if b:
        r = H._rect(b)
        sz = (r[2] - r[0], r[3] - r[1])
    try:
        with open(STATUS, "r", encoding="utf-8") as f:
            st = json.load(f) or {}
    except Exception:
        st = {}
    egg = st.get("egg") or {}
    print("  %-10s clicks=%-5s sticker_mode=%-5s vis=%-5s size=%-12s dbg=%r"
          % (tag, egg.get("clicks"), egg.get("sticker_mode"), vis, sz,
             st.get("debug")))


def main():
    pet = find_win("MiMo 桌宠")
    if not pet:
        print("找不到桌宠")
        return 1
    send_cmd({"action": "hidebubble"})
    time.sleep(1.2)
    snap("起点")

    print("发两次点击（间隔 80ms）:")
    user32.PostMessageW(pet, WM_LBUTTONDOWN, 1, lparam(116, 59))
    time.sleep(0.04)
    user32.PostMessageW(pet, WM_LBUTTONUP, 0, lparam(116, 59))
    time.sleep(0.08)
    user32.PostMessageW(pet, WM_LBUTTONDOWN, 1, lparam(116, 59))
    time.sleep(0.04)
    user32.PostMessageW(pet, WM_LBUTTONUP, 0, lparam(116, 59))

    for tag, dt in [("+0.05", 0.05), ("+0.25", 0.20), ("+0.55", 0.30),
                    ("+0.95", 0.40), ("+1.50", 0.55)]:
        time.sleep(dt)
        snap(tag)
    return 0


if __name__ == "__main__":
    sys.exit(main())
