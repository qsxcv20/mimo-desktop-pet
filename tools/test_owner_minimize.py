#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""test_owner_minimize.py — 查清是不是桌宠的 owner 绑定把 MiMo 最小化了。

Windows 语义：owned window 与 owner 的最小化是**双向联动**的
（owner 最小化 -> owned 隐藏；owned 最小化 -> owner 也最小化）。
所以桌宠一旦被最小化，MiMo 会被一起带走。

用法: python test_owner_minimize.py
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

PET_DIR = r"D:\桌面宠物\pet"


def state(tag):
    host = H.find_mimo_window(timeout=2, include_hidden=True)
    if not host:
        print("  [%s] 找不到 MiMo 窗口" % tag)
        return None, None
    return host, (bool(H.user32.IsIconic(host)),
                  bool(H.user32.IsWindowVisible(host)),
                  H._rect(host))


def restore():
    host = H.find_mimo_window(timeout=3, include_hidden=True)
    if host and H.user32.IsIconic(host):
        H.user32.ShowWindow(host, 9)     # SW_RESTORE
        time.sleep(1.2)
    return host


print("== 1. 恢复 MiMo ==")
restore()
h, s = state("初始")
print("   MiMo iconic=%s visible=%s rect=%s" % s)

print("\n== 2. 启动桌宠，观察 MiMo 是否被最小化 ==")
subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                             "pet_control.py"), "start"],
               stdout=subprocess.DEVNULL)
time.sleep(3)
for i in range(8):
    h, s = state("t+%ds" % (i + 1))
    if s is None:
        break
    print("   t+%-2ds  iconic=%s visible=%s rect=%s" % (i + 1, s[0], s[1], s[2]))
    if s[0]:
        print("   ★★ 桌宠一启动，MiMo 就被最小化了 —— 是 owner 联动最小化")
        break
    time.sleep(1)

print("\n== 3. 停止桌宠，再看 MiMo ==")
subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                             "pet_control.py"), "stop"],
               stdout=subprocess.DEVNULL)
time.sleep(2.5)
h, s = state("停止后")
print("   MiMo iconic=%s visible=%s rect=%s" % s)

if s and s[0]:
    print("   ★★ 桌宠退出后 MiMo 变成最小化 —— 退出流程里有问题")
    print("      （Qt 销毁 owned window 时可能把 owner 一起最小化）")
else:
    print("   ✓ 桌宠退出不影响 MiMo")
