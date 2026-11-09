#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
test_egg_live.py — 彩蛋交互的实机验证。

规则（当前实现）：
    单击        = 弹额度气泡（贴纸亮着时 = 只收起贴纸，不换贴纸）
    双击        = 弹一张表情包贴纸；贴纸开着时再双击 = 换下一张
    三击        = 不重弹贴纸，只切表情 + toast

为什么用 PostMessage 而不是真实鼠标：
    桌宠是 layered window，Windows 只在 alpha>0 的像素上做 hit test，
    当前帧的镂空区域（裙摆/帽尖）会把点击漏给下面的 MiMo 窗口，
    命中点极不稳定。PostMessage 走的是**完全相同的** Qt 处理函数
    （mousePressEvent / mouseReleaseEvent / mouseDoubleClickEvent），
    只是绕开了操作系统的命中测试，结果确定可复现。
    真实鼠标那条路径由本文件最后一节单独验证。

用法：
    python tools/test_egg_live.py 30
"""

import ctypes
import hashlib
import json
import os
import sys
import time
from ctypes import wintypes

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass  # pythonw.exe 下 sys.stdout 是 None
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "pet"))

import mimo_host as H                          # noqa: E402

user32 = H.user32
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
STATUS = r"D:\桌面宠物\pet\pet_status.json"
EGG = r"D:\桌面宠物\pet\egg_state.json"
CMD = r"D:\桌面宠物\pet\pet_cmd.json"
FAILS = []


def check(name, cond, extra=""):
    print("  [%s] %s %s" % ("PASS" if cond else "FAIL", name, extra))
    if not cond:
        FAILS.append(name)


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


def pet_click(x=116, y=59, pause=0.05):
    """给桌宠窗口发一次点击（窗口内坐标）。"""
    pet = find_win("MiMo 桌宠")
    if not pet:
        return None
    user32.PostMessageW(pet, WM_LBUTTONDOWN, 1, lparam(x, y))
    time.sleep(pause)
    user32.PostMessageW(pet, WM_LBUTTONUP, 0, lparam(x, y))
    return pet


def bubble():
    return find_win("MiMo 桌宠气泡")


def bubble_size():
    b = bubble()
    if not b:
        return None
    r = H._rect(b)
    return (r[2] - r[0], r[3] - r[1])


def bubble_visible():
    b = bubble()
    return bool(b and user32.IsWindowVisible(b))


def read_egg():
    try:
        with open(EGG, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}


def send_cmd(payload):
    payload["ts"] = int(time.time() * 1000)
    tmp = CMD + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    os.replace(tmp, CMD)


def wait_egg(pred, timeout=8.0):
    t0 = time.time()
    e = read_egg()
    while time.time() - t0 < timeout:
        e = read_egg()
        if pred(e):
            return e
        time.sleep(0.2)
    return e


HWND_TOPMOST = -1
HWND_NOTOPMOST = -2
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_SHOWWINDOW = 0x0040


def bring_to_front(hwnd):
    """把窗口提到最前（topmost 技巧，见 tools/force_front.py）。"""
    try:
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
    except Exception:
        pass


def main():
    n_target = int(sys.argv[1]) if len(sys.argv) > 1 else 30

    mimo = H.find_mimo_window(timeout=8, include_hidden=True)
    if not mimo:
        print("找不到 MiMo 窗口")
        return 1
    pet = find_win("MiMo 桌宠")
    if not pet:
        print("找不到桌宠窗口")
        return 1
    print("MiMo=%s 桌宠=%s" % (hex(mimo), hex(pet)))

    # 真实鼠标会打到「屏幕上最上面的那个窗口」。如果别的应用
    # （比如同时开着的浏览器）盖在 MiMo 上面，点击就落在它身上，
    # 桌宠根本收不到。先把 MiMo 提到最前，整轮都在它上面跑。
    bring_to_front(mimo)
    time.sleep(0.8)

    # -- 重置 --
    # 把桌宠归位到确定状态：先收起气泡（模式回到「额度」），
    # 再重置计数。顺序不能反 —— 收起气泡的那一下单击也会把计数 +1，
    # 所以要「先收起、后重置」。
    send_cmd({"action": "hidebubble"})
    time.sleep(0.8)
    send_cmd({"action": "egg", "what": "reset"})
    time.sleep(1.2)
    e = wait_egg(lambda x: x.get("clicks") == 0, 6)
    check("重置后计数=0 且未解锁",
          e.get("clicks") == 0 and not e.get("unlocked"), str(e))
    check("起始没有气泡", not bubble_visible())

    # -- 单击 = 额度气泡 --
    print("\n== 单击：应弹额度气泡 ==")
    pet_click()
    time.sleep(1.4)
    sz = bubble_size()
    check("单击后气泡可见", bubble_visible())
    check("是额度气泡尺寸（约 214x172）",
          sz is not None and abs(sz[1] - 172) <= 6 and sz[0] <= 225,
          "%s" % (sz,))

    # -- 攒点击解锁 --
    print("\n== 连点到解锁 ==")
    c0 = read_egg().get("clicks") or 0
    for _ in range(n_target * 3 + 20):
        pet_click(pause=0.03)
        if read_egg().get("unlocked"):
            break
        time.sleep(0.05)
    e = wait_egg(lambda x: x.get("unlocked"), 8)
    check("已解锁", e.get("unlocked") is True,
          "计数=%s（点了 %s 次）" % (e.get("clicks"), (e.get("clicks") or 0) - c0))

    # -- 双击 = 贴纸 --
    print("\n== 双击：应弹贴纸气泡 ==")
    pet_click()
    time.sleep(0.12)
    pet_click()
    time.sleep(1.6)
    sz = bubble_size()
    check("双击后气泡可见", bubble_visible())
    check("是贴纸气泡尺寸（约 228x270）",
          sz is not None and abs(sz[1] - 270) <= 8 and sz[0] > 220,
          "%s" % (sz,))
    b = bubble()
    if b:
        owner = user32.GetWindowLongPtrW(b, H.GWLP_HWNDPARENT) or 0
        check("owner 仍是 MiMo", owner == mimo,
              "%s vs %s" % (hex(owner), hex(mimo)))
        br = H._rect(b)
        mr = H._rect(mimo)
        inside = (br[0] >= mr[0] and br[1] >= mr[1] and
                  br[2] <= mr[2] and br[3] <= mr[3])
        check("贴纸气泡在 MiMo 窗口内", inside, "%s vs %s" % (br, mr))

    # -- 三击 = 还是贴纸 --
    print("\n== 三击：应仍是贴纸 ==")
    pet_click()
    time.sleep(0.10)
    pet_click()
    time.sleep(0.10)
    pet_click()
    time.sleep(1.6)
    sz = bubble_size()
    check("三击后气泡可见", bubble_visible())
    check("三击仍是贴纸气泡尺寸",
          sz is not None and abs(sz[1] - 270) <= 8 and sz[0] > 220,
          "%s" % (sz,))

    # -- 真实鼠标：命中路径 --
    print("\n== 真实鼠标点击：命中路径 ==")
    # 真实鼠标会打到「屏幕上最上面的那个窗口」。如果别的应用
    # （比如同时开着的浏览器）盖在 MiMo 上面，点击就落在它身上，
    # 桌宠根本收不到。先把 MiMo 提到最前。
    bring_to_front(mimo)
    time.sleep(0.8)
    pet = find_win("MiMo 桌宠")
    r = H._rect(pet)
    w, h = r[2] - r[0], r[3] - r[1]
    # 桌宠是 layered window，操作系统只在 alpha>0 的像素上命中。
    # 固定一个点会随动画帧 / 表情变化而点空，所以多试几个候选点。
    candidates = [(116, 59), (110, 80), (100, 70), (125, 45),
                  (120, 100), (95, 95), (135, 60), (105, 50)]
    old = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(old))
    hit = False
    tried = None
    for (fx, fy) in candidates:
        cx = r[0] + int(w * fx / 220.0)
        cy = r[1] + int(h * fy / 220.0)
        before = read_egg().get("clicks") or 0
        user32.SetCursorPos(cx, cy)
        time.sleep(0.06)
        user32.mouse_event(0x0002, 0, 0, 0, 0)
        time.sleep(0.05)
        user32.mouse_event(0x0004, 0, 0, 0, 0)
        time.sleep(0.5)
        after = read_egg().get("clicks") or 0
        if after > before:
            hit = True
            tried = (fx, fy, cx, cy)
            break
    user32.SetCursorPos(old.x, old.y)
    check("真实鼠标点击能命中桌宠（点脸/胸位置）", hit,
          "命中窗口内坐标=%s 屏幕坐标=%s" % ((tried[0], tried[1]) if tried else None,
                                          (tried[2], tried[3]) if tried else None))

    print("\n结果: %s" % ("全部通过" if not FAILS else "失败 -> %s" % FAILS))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
