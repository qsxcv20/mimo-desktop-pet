#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""probe_double.py - 诊断双击为什么没弹贴纸。

依次测：
  1. 右键菜单「彩蛋表情包 -> 抽一张」能否弹贴纸（走 show_sticker）
  2. 命令通道 {"action":"egg","what":"sticker"} 能否弹贴纸
  3. PostMessage 双击能否触发 on_double_click
这样就能区分：是 show_sticker 坏了，还是双击仲裁没派发。
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


def bubble_size():
    b = find_win("MiMo 桌宠气泡")
    if not b:
        return None
    r = H._rect(b)
    return (r[2] - r[0], r[3] - r[1])


def visible():
    b = find_win("MiMo 桌宠气泡")
    return bool(b and user32.IsWindowVisible(b))


def send_cmd(payload):
    payload["ts"] = int(time.time() * 1000)
    tmp = CMD + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    os.replace(tmp, CMD)


def status():
    try:
        with open(STATUS, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}


def main():
    pet = find_win("MiMo 桌宠")
    print("桌宠 hwnd = %s" % (hex(pet) if pet else None))
    st = status()
    print("状态: %s" % json.dumps(st.get("egg"), ensure_ascii=False))

    # -- 1. 命令通道抽贴纸 --
    print("")
    print("== 命令通道抽一张贴纸 ==")
    send_cmd({"action": "hidebubble"})
    time.sleep(0.6)
    send_cmd({"action": "egg", "what": "sticker"})
    time.sleep(1.5)
    print("   气泡可见=%s 尺寸=%s" % (visible(), bubble_size()))

    # -- 2. PostMessage 双击 --
    print("")
    print("== PostMessage 双击 ==")
    send_cmd({"action": "hidebubble"})
    time.sleep(0.8)
    before = status().get("egg", {}).get("collected")
    user32.PostMessageW(pet, WM_LBUTTONDOWN, 1, lparam(116, 59))
    time.sleep(0.04)
    user32.PostMessageW(pet, WM_LBUTTONUP, 0, lparam(116, 59))
    time.sleep(0.08)
    user32.PostMessageW(pet, WM_LBUTTONDOWN, 1, lparam(116, 59))
    time.sleep(0.04)
    user32.PostMessageW(pet, WM_LBUTTONUP, 0, lparam(116, 59))
    time.sleep(1.8)
    st = status()
    print("   气泡可见=%s 尺寸=%s" % (visible(), bubble_size()))
    print("   egg=%s" % json.dumps(st.get("egg"), ensure_ascii=False))
    print("   manual=%s state=%s" % (st.get("manual"), st.get("state")))

    return 0


if __name__ == "__main__":
    sys.exit(main())
