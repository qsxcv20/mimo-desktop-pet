#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_gesture_live.py — 新交互规则的实机验证（真实鼠标）。

新规则（2026-11-09，用户定）：
    单击 = 额度气泡（贴纸亮着时单击 = 切回额度气泡「查看」）
    双击 = 表情包贴纸
    三击 = 只换表情（临时，Hold 秒后自动回到跟随 MiMo）
    默认 = 跟随 MiMo 状态自动切换表情

**为什么必须用真实鼠标**：
    PostMessage 投递到 Qt 会有 0.5~1 秒的延迟（实测），
    两次点击的间隔远超任何合理的双击判定窗口 -> 永远测不出双击。
    真实鼠标走的是正常输入路径，间隔和真人一致。

**怎么区分气泡类型**：优先读桌宠内部状态 `pet_status.json` 的
    `egg.sticker_mode`（= 气泡控件的 _sticker 字段，100% 可靠）；
    窗口尺寸只作兜底（额度 172 / 贴纸 270）。
两个尺寸**都不是硬指标**：额度气泡宽度随内容变（214~301），
高度随额度行数变（1~8 行 → 130~274px，续订后可能超过贴纸的 270）。
不靠像素颜色（贴纸 09 是深色底）。

**命中问题**：桌宠是 layered window，只在 alpha>0 的像素上命中。
    所以多试几个候选点，命中了就记下，后续复用。

用法:
    python tools/test_gesture_live.py
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

QUOTA_H = 172
STICKER_H = 270
TOL = 10

HWND_TOPMOST = -1
HWND_NOTOPMOST = -2
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_SHOWWINDOW = 0x0040

FAILS = []
HIT = None          # 命中的屏幕坐标


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


def bubble_size():
    b = find_win("MiMo 桌宠气泡")
    if not b:
        return None
    r = H._rect(b)
    return (r[2] - r[0], r[3] - r[1])


def bubble_visible():
    b = find_win("MiMo 桌宠气泡")
    return bool(b and user32.IsWindowVisible(b))


def status_fresh(max_age_ms=3000):
    """状态文件够新吗（桌宠每 1 秒刷新一次 pet_status.json）。"""
    upd = status().get("updated") or 0
    if not upd:
        return False
    return (int(time.time() * 1000) - int(upd)) <= max_age_ms


def bubble_kind():
    """返回 'sticker' / 'quota' / None。

    判据优先级：
      1. 桌宠内部状态 pet_status.json -> egg.sticker_mode（**主判据**）
         它直接来自气泡控件的 _sticker 字段，100% 可靠、不受尺寸影响。
      2. 窗口高度（**兜底**）：贴纸 270 / 额度 172。

    为什么不能只靠高度：额度气泡高度随额度行数变化
    （1~8 行 → 130~274px），用户续订后可能超过贴纸的 270px。
    宽度更不行 —— 实测 214（selftest mock）~301（实机）随内容变。
    """
    if status_fresh():
        sm = status().get("egg") or {}
        if "sticker_mode" in sm:
            return "sticker" if sm.get("sticker_mode") else "quota"
    sz = bubble_size()
    if not sz:
        return None
    if abs(sz[1] - STICKER_H) <= TOL:
        return "sticker"
    if abs(sz[1] - QUOTA_H) <= TOL:
        return "quota"
    return None


def wait_kind(expected, timeout=3.0):
    """等气泡变成期望模式；返回最后一次读到的值（超时返回最后值）。"""
    deadline = time.time() + timeout
    last = None
    while True:
        last = bubble_kind()
        if last == expected:
            return last
        if time.time() >= deadline:
            return last
        time.sleep(0.15)


def status():
    try:
        with open(STATUS, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}


def clicks():
    return (status().get("egg") or {}).get("clicks") or 0


def send_cmd(payload):
    payload["ts"] = int(time.time() * 1000)
    tmp = CMD + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    os.replace(tmp, CMD)


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


def click(x, y):
    user32.SetCursorPos(int(x), int(y))
    time.sleep(0.02)
    user32.mouse_event(0x0002, 0, 0, 0, 0)
    time.sleep(0.03)
    user32.mouse_event(0x0004, 0, 0, 0, 0)


def find_hit():
    """找一个能命中桌宠实心区域的屏幕坐标。"""
    global HIT
    if HIT:
        return HIT
    pet = find_win("MiMo 桌宠")
    if not pet:
        return None
    r = H._rect(pet)
    w = r[2] - r[0]
    h = r[3] - r[1]
    cands = [(116, 59), (110, 80), (100, 70), (120, 45), (108, 95),
             (125, 60), (95, 60), (112, 110), (100, 55), (118, 75),
             (105, 65), (112, 50)]
    for (fx, fy) in cands:
        cx = r[0] + int(w * fx / 220.0)
        cy = r[1] + int(h * fy / 220.0)
        before = clicks()
        click(cx, cy)
        time.sleep(0.9)
        if clicks() > before:
            HIT = (cx, cy)
            return HIT
    return None


def main():
    mimo = H.find_mimo_window(timeout=8, include_hidden=True)
    if not find_win("MiMo 桌宠"):
        print("找不到桌宠窗口 —— 先启动桌宠")
        return 1
    print("MiMo=%s" % (hex(mimo) if mimo else None))

    # 真实鼠标要点在 MiMo 上面，先把它提到最前
    if mimo:
        bring_to_front(mimo)
        time.sleep(0.8)

    send_cmd({"action": "hidebubble"})
    time.sleep(1.0)
    send_cmd({"action": "auto"})
    time.sleep(0.6)
    check("起点没有气泡", not bubble_visible())

    hit = find_hit()
    if not hit:
        print("找不到能命中的点（桌宠可能在后台）")
        return 1
    print("命中点 = %s" % (hit,))
    cx, cy = hit

    # ================= 1. 单击 = 额度气泡 =================
    print("")
    print("== 1. 单击：应弹额度气泡 ==")
    send_cmd({"action": "hidebubble"})
    time.sleep(0.9)
    click(cx, cy)
    time.sleep(1.2)
    check("气泡可见", bubble_visible(), str(bubble_size()))
    check("是额度气泡", wait_kind("quota") == "quota",
          "%s kind=%s" % (bubble_size(), bubble_kind()))

    # ================= 2. 双击 = 贴纸 =================
    print("")
    print("== 2. 双击：应弹贴纸 ==")
    send_cmd({"action": "hidebubble"})
    time.sleep(0.9)
    click(cx, cy)
    time.sleep(0.09)
    click(cx, cy)
    time.sleep(1.6)
    check("双击后是贴纸气泡", wait_kind("sticker") == "sticker",
          "%s kind=%s" % (bubble_size(), bubble_kind()))

    # ================= 3. 贴纸亮着时单击 = 切回额度 =================
    print("")
    print("== 3. 贴纸亮着时单击：应切回额度 ==")
    click(cx, cy)
    time.sleep(1.4)
    check("单击后切回额度气泡", wait_kind("quota") == "quota",
          "%s kind=%s" % (bubble_size(), bubble_kind()))

    # ================= 4. 三击 = 只换表情 =================
    print("")
    print("== 4. 三击：应只换表情，不弹贴纸 ==")
    send_cmd({"action": "hidebubble"})
    time.sleep(0.9)
    before = status().get("state")
    click(cx, cy)
    time.sleep(0.09)
    click(cx, cy)
    time.sleep(0.09)
    click(cx, cy)
    time.sleep(1.6)
    check("三击后不是贴纸气泡", wait_kind("quota", timeout=1.2) != "sticker",
          "%s kind=%s" % (bubble_size(), bubble_kind()))
    st = status()
    check("三击切了表情", st.get("state") != before or bool(st.get("manual")),
          "before=%s after=%s manual=%s" % (before, st.get("state"),
                                            st.get("manual")))

    # ================= 5. 临时表情到期自动回到跟随 =================
    print("")
    print("== 5. 临时表情到期：应自动回到跟随 MiMo ==")
    time.sleep(0.8)
    st = status()
    check("临时期间是手动表情", bool(st.get("manual")),
          "manual=%s" % st.get("manual"))
    time.sleep(5.0)
    st = status()
    check("到期后自动解除手动锁", not st.get("manual"),
          "manual=%s state=%s" % (st.get("manual"), st.get("state")))

    print("")
    print("结果: %s" % ("全部通过" if not FAILS else "失败 -> %s" % FAILS))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
