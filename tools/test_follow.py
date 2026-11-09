#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""test_follow.py — 验证桌宠是否严格跟随 MiMo 窗口。

测试项：
  1. 移动 MiMo 窗口 -> 桌宠相对 MiMo 客户区的坐标不变
  2. 最小化 / 恢复  -> 桌宠跟着隐藏 / 回来，且仍绑定 owner
  3. 缩放 MiMo 窗口 -> 桌宠仍被夹在客户区内

⚠️ 重要：直接用 SetWindowPos 改 Electron 窗口尺寸、以及最小化/恢复，
   都可能让 Chromium 的渲染层挂掉（表现为窗口只剩背景色，一片黑）。
   所以本脚本最后会做一次「渲染层健康检查」，发现黑屏就自动重启 MiMo。
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

from PySide6.QtWidgets import QApplication
import mimo_host as H

app = QApplication(sys.argv)


def find_pet():
    import ctypes
    from ctypes import wintypes
    out = []
    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def cb(h, _l):
        if H._text(h) == "MiMo 桌宠":
            out.append(h)
        return True

    H.user32.EnumWindows(WNDENUMPROC(cb), 0)
    return out[0] if out else None


def rel_pos(host, pet):
    ox, oy = H.client_to_screen(host, 0, 0)
    pr = H._rect(pet)
    return (pr[0] - ox, pr[1] - oy), H._rect(host), pr


def render_alive(host):
    """检查 Chromium 渲染层是否还活着（非背景像素占比）。"""
    from grab_window import grab
    im, _ = grab(host)
    rgb = im.convert("RGB")
    px = list(rgb.getdata())
    bg = sum(1 for p in px if abs(p[0] - 30) < 6 and abs(p[1] - 30) < 6
             and abs(p[2] - 30) < 6)
    return 100.0 * (len(px) - bg) / len(px)


ok = True
host = H.find_mimo_window(timeout=8, include_hidden=True)
if not host:
    print("!! 找不到 MiMo 窗口")
    sys.exit(1)
time.sleep(1.0)
pet = find_pet()
if not pet:
    print("!! 找不到桌宠窗口")
    sys.exit(1)

print("MiMo hwnd =", hex(host), " 桌宠 hwnd =", hex(pet))
print()

# ---- 1. 移动窗口 ----
r0 = H._rect(host)
rel0, h0, p0 = rel_pos(host, pet)
print("初始 MiMo rect=%s  桌宠相对客户区=%s" % (h0, rel0))

target = (h0[0] - 260, h0[1] + 90)
H.user32.SetWindowPos(host, 0, target[0], target[1], 0, 0,
                      H.SWP_NOSIZE | H.SWP_NOZORDER | H.SWP_NOACTIVATE)
time.sleep(1.2)
rel1, h1, p1 = rel_pos(host, pet)
print("移动到 rect=%s  桌宠相对客户区=%s" % (h1, rel1))
moved = (h1[0] != h0[0] or h1[1] != h0[1])
same = abs(rel1[0] - rel0[0]) <= 3 and abs(rel1[1] - rel0[1]) <= 3
print("  -> 窗口移动了: %s ; 桌宠相对位置不变: %s" % ("是" if moved else "否",
                                                  "是 ✓" if same else "否 ✗"))
ok = ok and moved and same

# ---- 2. 最小化 / 恢复 ----
H.user32.ShowWindow(host, 6)          # SW_MINIMIZE
time.sleep(1.4)
vis_pet = H.user32.IsWindowVisible(pet)
print("MiMo 最小化后: 桌宠 visible=%s" % vis_pet)
print("  -> 桌宠跟着隐藏: %s" % ("是 ✓" if not vis_pet else "否 ✗"))
ok = ok and not vis_pet

H.user32.ShowWindow(host, 9)          # SW_RESTORE
time.sleep(1.8)
vis_pet = H.user32.IsWindowVisible(pet)
owner = H.user32.GetWindowLongPtrW(pet, H.GWLP_HWNDPARENT) or 0
print("MiMo 恢复后: 桌宠 visible=%s  owner=%s (MiMo=%s)"
      % (vis_pet, hex(owner), hex(host)))
print("  -> 桌宠自动回来且仍绑定: %s"
      % ("是 ✓" if vis_pet and owner == host else "否 ✗"))
ok = ok and vis_pet and owner == host

# ---- 3. 缩放窗口（放最后，最容易搞坏渲染层）----
H.user32.SetWindowPos(host, 0, 0, 0, h1[2] - h1[0] - 320, h1[3] - h1[1] - 120,
                      H.SWP_NOMOVE | H.SWP_NOZORDER | H.SWP_NOACTIVATE)
time.sleep(1.5)
h2 = H._rect(host)
p2 = H._rect(pet)
inside = (h2[0] <= p2[0] and h2[1] <= p2[1] and p2[2] <= h2[2] and p2[3] <= h2[3])
cw, ch = H.client_size(host)
print("缩放后 MiMo rect=%s client=%dx%d  桌宠 rect=%s" % (h2, cw, ch, p2))
print("  -> 桌宠仍在客户区内: %s" % ("是 ✓" if inside else "否 ✗"))
ok = ok and inside

# ---- 4. 恢复原状 ----
H.user32.SetWindowPos(host, 0, h0[0], h0[1], h0[2] - h0[0], h0[3] - h0[1],
                      H.SWP_NOZORDER | H.SWP_NOACTIVATE)
time.sleep(1.0)
H.user32.RedrawWindow(host, None, None,
                      H.RDW_INVALIDATE | H.RDW_ERASE | H.RDW_ALLCHILDREN |
                      H.RDW_UPDATENOW)
time.sleep(1.0)
print("已恢复原状: rect=%s" % (H._rect(host),))

# ---- 5. 渲染层健康检查 ----
try:
    pct = render_alive(host)
    alive = pct >= 0.5
    print("渲染层非背景像素 %.2f%% -> %s" % (pct, "正常 ✓" if alive else "黑屏 ✗"))
except Exception as e:
    alive = False
    print("渲染层检查失败: %s" % e)

if not alive:
    print("\n检测到渲染层黑屏，正在自动重启 MiMo …")
    r = subprocess.call([sys.executable,
                         os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                      "restart_mimo.py")])
    print("重启返回码:", r)
    ok = ok and (r == 0)

print("\n%s" % ("全部通过 ✓" if ok else "有项目未通过 ✗"))
sys.exit(0 if ok else 1)
