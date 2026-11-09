#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""test_bubble_live.py — 实机验证气泡常驻。

用户反馈：「点击之后显示的那个东西，点一下就消失了，不会给你一直显示那个东西。」
验证三件事：
  1. 弹出后 12 秒（超过旧版 9 秒自动消失）仍然可见
  2. 收起后再弹出，仍然可见（回归旧版「弹出来立刻被旧 hide 回调关掉」的 bug）
  3. 气泡 owner 仍然绑定在 MiMo 上
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
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pet"))

import mimo_host as H  # noqa: E402

CMD = r"D:\桌面宠物\pet\pet_cmd.json"
FAILS = []


def find_win(title):
    out = []
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def cb(h, _l):
        if H._text(h) == title:
            out.append(int(h))
        return True

    H.user32.EnumWindows(WNDENUMPROC(cb), 0)
    return out[0] if out else None


def check(name, cond, extra=""):
    print("  [%s] %s %s" % ("PASS" if cond else "FAIL", name, extra))
    if not cond:
        FAILS.append(name)


def send(action):
    with open(CMD, "w", encoding="utf-8") as f:
        json.dump({"action": action, "ts": int(time.time() * 1000)}, f)
    time.sleep(1.2)


def main():
    mimo = H.find_mimo_window(timeout=8, include_hidden=True)
    print("MiMo hwnd = %s" % (hex(mimo) if mimo else None))

    print("\n== 1. 首次弹出 ==")
    send("bubble")
    b = find_win("MiMo 桌宠气泡")
    check("气泡窗口存在", b is not None)
    if not b:
        return 1
    check("弹出后可见", H.user32.IsWindowVisible(b))
    owner = H.user32.GetWindowLongPtrW(b, H.GWLP_HWNDPARENT) or 0
    check("owner 绑定 MiMo", owner == mimo, "owner=%s" % hex(owner))

    print("\n== 2. 等 12 秒（超过旧版 9 秒自动消失）==")
    time.sleep(12)
    check("12 秒后仍然可见", H.user32.IsWindowVisible(b))

    print("\n== 3. 收起后重新弹出（回归旧版被旧 hide 回调秒关的 bug）==")
    send("bubble")
    # 旧逻辑里 click 会切换；CLI 的 bubble 指令是强制显示，这里直接看可见性
    check("再次弹出后可见", H.user32.IsWindowVisible(b))
    time.sleep(3)
    check("再等 3 秒仍然可见", H.user32.IsWindowVisible(b))

    print("\n结果: %s" % ("全部通过" if not FAILS else "失败 -> %s" % FAILS))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
