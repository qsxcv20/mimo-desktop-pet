#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""test_sticker_switch.py — 实机验证贴纸（彩蛋）的点击规则。

规则（2026-11-09 用户新定）：
    双击      = 弹出一张贴纸；贴纸开着时再双击 = 换下一张
    单击      = 额度气泡；**贴纸开着时单击 = 切回额度气泡**（查看用量）

断言指标（都用客观状态，不靠截图）：
  * egg_state.json 的 idx：只有 _next_sticker() 会改它 -> 变了 = 换了张
    （seen 不能用来断言：它按 n*2 截尾，长度不单调）
  * pet_status.json 的 egg.clicks：单击 +1，双击 +2（release + dblclick）
  * 气泡窗口的 PrintWindow 哈希：贴纸换了画面就变

点击用 PostMessage 直接发给桌宠窗口，不经过鼠标命中测试 ——
Windows 的 layered window 只在 alpha>0 的像素上做 hit test，桌宠当前帧
的镂空区域会把点击漏给下面的 MiMo 窗口，命中点极不稳定。PostMessage
走的是完全相同的 Qt 处理函数（mousePressEvent / mouseReleaseEvent /
mouseDoubleClickEvent）。

用法：
    python tools/test_sticker_switch.py
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

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EGG_STATE = os.path.join(ROOT, "pet", "egg_state.json")
STATUS = os.path.join(ROOT, "pet", "pet_status.json")
CMD = os.path.join(ROOT, "pet", "pet_cmd.json")
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


def click_msg(hwnd, x, y):
    user32.PostMessageW(hwnd, WM_LBUTTONDOWN, 1, lparam(x, y))
    time.sleep(0.04)
    user32.PostMessageW(hwnd, WM_LBUTTONUP, 0, lparam(x, y))


def click_pet():
    """给桌宠窗口发一次点击（客户区坐标 = 窗口内坐标）。"""
    pet = find_win("MiMo 桌宠")
    if not pet:
        return None
    click_msg(pet, 116, 59)      # 脸/胸位置（帧内 135,69）
    return pet


def double_click_pet():
    pet = find_win("MiMo 桌宠")
    if not pet:
        return None
    click_msg(pet, 116, 59)
    time.sleep(0.12)
    click_msg(pet, 116, 59)
    return pet


def bubble():
    return find_win("MiMo 桌宠气泡")


def bubble_size():
    """气泡窗口尺寸 (宽, 高)。"""
    hwnd = bubble()
    if not hwnd:
        return None
    r = H._rect(hwnd)
    return (r[2] - r[0], r[3] - r[1])


def bubble_visible():
    b = bubble()
    return bool(b and user32.IsWindowVisible(b))


def status():
    try:
        with open(STATUS, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}


def status_fresh(max_age_ms=3000):
    upd = status().get("updated") or 0
    if not upd:
        return False
    return (int(time.time() * 1000) - int(upd)) <= max_age_ms


def bubble_kind():
    """返回 'sticker' / 'quota' / None。

    主判据 = pet_status.json 的 egg.sticker_mode（气泡控件 _sticker 字段，
    100% 可靠）；窗口高度只作兜底（贴纸 270 / 额度 172）——
    额度气泡高度随额度行数变（130~274px），续订后会失效。
    """
    if status_fresh():
        sm = status().get("egg") or {}
        if "sticker_mode" in sm:
            return "sticker" if sm.get("sticker_mode") else "quota"
    sz = bubble_size()
    if not sz:
        return None
    if abs(sz[1] - 270) <= 10:
        return "sticker"
    if abs(sz[1] - 172) <= 10:
        return "quota"
    return None


def wait_kind(expected, timeout=3.0):
    deadline = time.time() + timeout
    last = None
    while True:
        last = bubble_kind()
        if last == expected:
            return last
        if time.time() >= deadline:
            return last
        time.sleep(0.15)


class BMI(ctypes.Structure):
    _fields_ = [("biSize", wintypes.DWORD),
                ("biWidth", ctypes.c_long),
                ("biHeight", ctypes.c_long),
                ("biPlanes", wintypes.WORD),
                ("biBitCount", wintypes.WORD),
                ("biCompression", wintypes.DWORD),
                ("biSizeImage", wintypes.DWORD),
                ("biXPelsPerMeter", ctypes.c_long),
                ("biYPelsPerMeter", ctypes.c_long),
                ("biClrUsed", wintypes.DWORD),
                ("biClrImportant", wintypes.DWORD)]


def bubble_hash():
    """气泡窗口位图的 md5 —— 贴纸换了哈希就变。"""
    hwnd = bubble()
    if not hwnd:
        return None
    u = ctypes.windll.user32
    r = H._rect(hwnd)
    w, h = r[2] - r[0], r[3] - r[1]
    if w <= 0 or h <= 0:
        return None
    hdc = u.GetWindowDC(hwnd)
    mdc = ctypes.windll.gdi32.CreateCompatibleDC(hdc)
    bmp = ctypes.windll.gdi32.CreateCompatibleBitmap(hdc, w, h)
    ctypes.windll.gdi32.SelectObject(mdc, bmp)
    u.PrintWindow(hwnd, mdc, 2)

    bi = BMI()
    bi.biSize = ctypes.sizeof(BMI)
    bi.biWidth = w
    bi.biHeight = -h
    bi.biPlanes = 1
    bi.biBitCount = 32
    bi.biCompression = 0
    buf = ctypes.create_string_buffer(w * h * 4)
    ctypes.windll.gdi32.GetDIBits(mdc, bmp, 0, h, buf, ctypes.byref(bi), 0)
    ctypes.windll.gdi32.DeleteObject(bmp)
    ctypes.windll.gdi32.DeleteDC(mdc)
    u.ReleaseDC(hwnd, hdc)
    return hashlib.md5(bytes(buf)).hexdigest()[:12]


def egg_idx():
    """egg_state.json 的 idx —— 只有换贴纸才会变。"""
    try:
        with open(EGG_STATE, "r", encoding="utf-8") as f:
            return (json.load(f) or {}).get("idx")
    except Exception:
        return None


def seen_len():
    try:
        with open(EGG_STATE, "r", encoding="utf-8") as f:
            return len((json.load(f) or {}).get("seen") or [])
    except Exception:
        return -1


def clicks():
    try:
        with open(STATUS, "r", encoding="utf-8") as f:
            return ((json.load(f) or {}).get("egg") or {}).get("clicks")
    except Exception:
        return None


def send_cmd(payload):
    payload["ts"] = int(time.time() * 1000)
    tmp = CMD + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    os.replace(tmp, CMD)


def main():
    pet = find_win("MiMo 桌宠")
    if not pet:
        print("找不到桌宠窗口 —— 先启动桌宠")
        return 1

    gr = wintypes.RECT()
    cr = wintypes.RECT()
    user32.GetWindowRect(pet, ctypes.byref(gr))
    user32.GetClientRect(pet, ctypes.byref(cr))
    print("桌宠 hwnd=%s  窗口 %dx%d  客户区 %dx%d"
          % (hex(pet), gr.right - gr.left, gr.bottom - gr.top,
             cr.right - cr.left, cr.bottom - cr.top))

    # 直接解锁，跳过 30 次点击
    send_cmd({"action": "egg", "what": "unlock"})
    time.sleep(1.5)

    # -- 1. 双击出贴纸 --
    print("\n== 双击：应弹出贴纸 ==")
    i0, c0 = egg_idx(), clicks()
    double_click_pet()
    time.sleep(1.6)
    i1, c1 = egg_idx(), clicks()
    print("   clicks %s -> %s   idx %s -> %s   seen %s"
          % (c0, c1, i0, i1, seen_len()))
    check("双击后气泡可见", bubble_visible())
    check("双击后计数 +2（release + dblclick）", c1 == c0 + 2,
          "%s -> %s" % (c0, c1))
    check("双击换了一张贴纸 (idx %s -> %s)" % (i0, i1), i1 != i0)
    h1 = bubble_hash()
    print("   贴纸气泡哈希 = %s" % h1)

    # -- 2. 再双击 = 换下一张 --
    print("\n== 再双击：应换成下一张贴纸 ==")
    double_click_pet()
    time.sleep(1.6)
    i2 = egg_idx()
    check("气泡仍可见", bubble_visible())
    check("又换了一张 (idx %s -> %s)" % (i1, i2), i2 != i1)
    h2 = bubble_hash()
    print("   贴纸气泡哈希 = %s" % h2)
    check("画面确实变了", h1 != h2, "%s vs %s" % (h1, h2))

    # -- 3. 贴纸亮着时单击 = 切回额度气泡（2026-11-09 新规则） --
    #
    # 旧规则是「单击只收起贴纸」，新规则改成
    # 「有表情包单击是查看」= 切回额度气泡去看用量。
    print("\n== 贴纸亮着时单击：应切回额度气泡 ==")
    i3 = egg_idx()
    click_pet()
    time.sleep(1.4)
    i4 = egg_idx()
    check("单击没有换贴纸 (idx %s -> %s)" % (i3, i4), i4 == i3)
    sz = bubble_size()
    check("单击后是额度气泡（不是贴纸）",
          wait_kind("quota") == "quota",
          "%s kind=%s" % (sz, bubble_kind()))

    # -- 4. 切回额度后再双击 = 能重新出贴纸 --
    print("\n== 收起后再双击：应重新出贴纸 ==")
    i5 = egg_idx()
    double_click_pet()
    time.sleep(1.6)
    i6 = egg_idx()
    check("气泡重新出现", bubble_visible())
    check("又换了一张 (idx %s -> %s)" % (i5, i6), i6 != i5)

    print("\n结果: %s" % ("全部通过" if not FAILS else "失败 -> %s" % FAILS))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
