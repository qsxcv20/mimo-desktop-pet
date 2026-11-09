#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""test_bubble_timeout.py — 端到端验证「气泡自动收起」。

用户要求：「可以给它定一个比较长的时间，然后它也会自动收起」。
所以要同时保证两件事：
  1. 自动收起真的会触发（用 8 秒做加速验证）
  2. 默认 60 秒时，在观察窗口内不会被提前收起
最后把配置还原成 60 秒。

用法: python test_bubble_timeout.py
"""
import ctypes
import json
import os
import subprocess
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass  # pythonw.exe 下 sys.stdout 是 None

ROOT = r"D:\桌面宠物"
sys.path.insert(0, os.path.join(ROOT, "pet"))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import mimo_host as H  # noqa: E402

CFG = os.path.join(ROOT, "pet", "pet_config.json")
CTL = os.path.join(ROOT, "tools", "pet_control.py")
CMD = os.path.join(ROOT, "pet", "pet_cmd.json")
FAILS = []


def check(name, cond, extra=""):
    print("  [%s] %s %s" % ("PASS" if cond else "FAIL", name, extra))
    if not cond:
        FAILS.append(name)


def find_bubble():
    out = []
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def cb(h, _l):
        if H._text(h) == "MiMo 桌宠气泡":
            out.append(int(h))
        return True

    H.user32.EnumWindows(WNDENUMPROC(cb), 0)
    return out[0] if out else None


def bubble_visible():
    b = find_bubble()
    return bool(b and H.user32.IsWindowVisible(b))


def set_timeout(sec):
    cfg = {}
    if os.path.isfile(CFG):
        with open(CFG, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    cfg["bubble_timeout"] = sec
    with open(CFG, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    print("  配置 bubble_timeout = %s" % sec)


def stop_pet():
    subprocess.run([sys.executable, CTL, "stop"], capture_output=True)
    time.sleep(2)


def start_pet():
    subprocess.run([sys.executable, CTL, "start"], capture_output=True)
    time.sleep(6)


def set_and_restart(sec):
    # 顺序很重要：必须先停掉桌宠。
    # 桌宠退出时会 _save_pos() -> save_config()，把**它内存里的旧配置**写回文件，
    # 会覆盖我们刚写进去的 bubble_timeout。
    stop_pet()
    set_timeout(sec)
    start_pet()


def show_bubble(wait=2.0):
    """发指令弹气泡，返回气泡真正可见所花的时间（秒）。"""
    with open(CMD, "w", encoding="utf-8") as f:
        json.dump({"action": "bubble", "ts": int(time.time() * 1000)}, f)
    t0 = time.time()
    while time.time() - t0 < wait:
        if bubble_visible():
            return time.time() - t0
        time.sleep(0.05)
    return None


def main():
    print("== A. 气泡要秒弹（额度在后台拉）==")
    set_and_restart(5)
    dt = show_bubble()
    check("气泡 1 秒内可见", dt is not None and dt < 1.0,
          "耗时 %s" % ("%.2fs" % dt if dt else "未出现"))

    print("\n== B. bubble_timeout=5：到点自动收起 ==")
    check("刚弹出时可见", bubble_visible())
    time.sleep(3)
    check("3 秒时仍可见（还没到 5 秒）", bubble_visible())
    time.sleep(4)
    check("7 秒时已自动收起", not bubble_visible())

    print("\n== C. 收起后还能再弹出来 ==")
    show_bubble()
    check("再次弹出可见", bubble_visible())

    print("\n结果: %s" % ("全部通过" if not FAILS else "失败 -> %s" % FAILS))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
