#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_gesture.py — 单击 / 双击 / 三击手势仲裁的纯逻辑自测（不开 GUI）。

2026-11-09 新规则（用户定）：
    单击 = 额度气泡（贴纸亮着时单击 = 切回额度气泡「查看」）
    双击 = 表情包贴纸
    三击 = 只换表情（临时，Hold 秒后自动回到跟随 MiMo）
    默认 = 跟随 MiMo 状态自动切换表情

为什么要有这个测试：
    多击事件在真机上很难稳定复现（layered window 命中测试、
    时序抖动），但仲裁逻辑本身是纯计数 + 定时器。
    这里把 Windows/Qt 的真实事件序列喂进去，穷举各种时序，
    断言「最终派发的语义」正确。

Windows / Qt 的真实事件序列（本轮实测踩坑后确认）：
    单击：press -> release
    双击：press -> release -> dblclick -> release
          Windows 把第 2 次「按下」换成 WM_LBUTTONDBLCLK，
          所以 dblclick = 第 2 次点击已发生（只打标记，不计数），
          它后面那个 release 才是第 2 次点击的计数点。
    三击：press -> release -> dblclick -> release -> press -> release
          第 3 次点击又是普通的 press/release。
    四击：… -> press -> release -> dblclick -> release

仲裁模型（与 pet/mimo_pet.py 的 PetWindow 一致）：
    计数只认 release（= 真实物理点击数）
    dblclick 只设 _double_marked 标记
    结算：1 次 release 且无标记 = 单击
          2 次 release 且有标记 = 双击
          >=3 次 release = 三击

被测逻辑在 pet/mimo_pet.py 的 PetWindow 里（_register_click /
_resolve_gesture）。这里复制一份等价实现（Arbiter），
并在最后逐条核对源文件的常量与函数名。

用法:
    python tools/test_gesture.py
"""

import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass  # pythonw.exe 下 sys.stdout 是 None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FAILED = []


def check(name, cond, extra=""):
    print("  [%s] %s %s" % ("PASS" if cond else "FAIL", name, extra))
    if not cond:
        FAILED.append(name)


class Arbiter(object):
    """PetWindow 手势仲裁的等价实现（用于测试）。

    与 pet/mimo_pet.py 的 PetWindow 一致：
      - **只数 release**（= 真实物理点击数）
        1 = 单击，2 = 双击，>=3 = 三击
      - dblclick 事件不参与计数（Windows 的 DBLCLK 合成
        在很多场景下不发生，不能依赖它）
      - 每次物理点击都调 on_tap()（彩蛋计数与手势解耦）
      - 计数 >= 3 立刻结算；否则等 GESTURE_WAIT_MS
      - 两次点击间隔超过 GESTURE_WINDOW_MS 则断串重数
    """

    GESTURE_WAIT_MS = 220
    GESTURE_WINDOW_MS = 700

    def __init__(self):
        self.clicks = 0
        self.last_click_at = 0.0
        self.now = 0.0
        self.settle_at = 0.0
        self.results = []
        self.taps = 0

    # -- 事件入口 --
    def release(self, t):
        self.now = t
        self.register_click()

    def dblclick(self, t):
        """dblclick 不参与计数（见类注释）。"""
        self.now = t

    # -- 内部 --
    def register_click(self):
        if self.now - self.last_click_at > self.GESTURE_WINDOW_MS / 1000.0:
            self.clicks = 0
        self.last_click_at = self.now
        self.clicks += 1
        self.taps += 1
        if self.clicks >= 3:
            self.settle_at = 0.0
            self.resolve()
            return
        self.settle_at = self.now + self.GESTURE_WAIT_MS / 1000.0

    def resolve(self):
        n = self.clicks
        self.clicks = 0
        if n <= 0:
            return
        if n == 1:
            self.results.append("single")
        elif n == 2:
            self.results.append("double")
        else:
            self.results.append("triple")

    def tick(self, t):
        self.now = t
        if self.clicks and self.settle_at and t >= self.settle_at:
            self.settle_at = 0.0
            self.resolve()

    def last(self):
        return self.results[-1] if self.results else None

def drive(events, step=0.05, total=2.0):
    """喂一串事件，推进时钟到结束，返回 Arbiter。"""
    a = Arbiter()
    t = 0.0
    for kind in events:
        if kind == "r":
            a.release(t)
        elif kind == "d":
            a.dblclick(t)
        t += step
    while t < total:
        a.tick(t)
        t += step
    return a


def main():
    print("== 手势语义 ==")

    # 1) 单击：press -> release
    a = drive(["r"])
    check("单击 -> single", a.last() == "single", str(a.results))

    # 2) 双击：press -> release -> dblclick -> release
    a = drive(["r", "d", "r"])
    check("双击 -> double", a.last() == "double", str(a.results))

    # 3) 三击：press -> release -> dblclick -> release -> press -> release
    a = drive(["r", "d", "r", "r"])
    check("三击 -> triple", a.last() == "triple", str(a.results))

    # 4) 只按了一次（dblclick 不算点击）
    a = drive(["r", "d"])
    check("dblclick 不算点击 -> 仍判 single",
          a.last() == "single", str(a.results))

    # 5) 四击：前 3 次结算成 triple，第 4 次是独立的一轮单击
    a = drive(["r", "d", "r", "r", "d", "r"])
    check("四击 -> triple + single（每次点击都独立结算）",
          a.results == ["triple", "single"], str(a.results))

    print("\n== 连点保护（彩蛋解锁靠连点） ==")

    # 6) 连点 30 次 —— 每个物理点击都要计数
    a = Arbiter()
    t = 0.0
    for _ in range(30):
        a.release(t)
        t += 0.12
    while t < 3.0:
        a.tick(t)
        t += 0.05
    check("连点 30 次 -> 物理计数 = 30", a.taps == 30, "实际 %d" % a.taps)

    # 7) 慢速点击（间隔 750ms > GESTURE_WINDOW_MS 700ms）-> 每次独立
    a = Arbiter()
    t = 0.0
    for _ in range(3):
        a.release(t)
        # 推进时钟到结算之后，让这一次单击先结掉
        a.tick(t + 0.30)
        t += 0.75
    while t < 4.0:
        a.tick(t)
        t += 0.05
    check("慢速三连（间隔 750ms）-> 3 个独立单击",
          a.results == ["single"] * 3, str(a.results))

    # 8) 单击后很久再来一次双击 -> 单、双，互不串台
    a = Arbiter()
    a.release(0.0)
    a.tick(0.3)              # 单击结算
    a.release(1.0)
    a.dblclick(1.05)
    a.release(1.10)
    while a.now < 2.0:
        a.tick(a.now + 0.05)
    check("隔很久的「单击 + 双击」-> 单、双，互不串台",
          a.results == ["single", "double"], str(a.results))

    # 9) 双击后紧跟第三次点击 -> 三击（不能停在双击）
    a = drive(["r", "d", "r", "r"], step=0.12)
    check("双击后立刻第三次 -> triple（不是 double）",
          a.last() == "triple", str(a.results))

    print("\n== 与源码一致性 ==")
    src = os.path.join(ROOT, "pet", "mimo_pet.py")
    with open(src, "r", encoding="utf-8") as f:
        text = f.read()
    check("源码有 GESTURE_WAIT_MS", "GESTURE_WAIT_MS" in text)
    check("源码有 TRIPLE_WAIT_MS", "TRIPLE_WAIT_MS" in text)
    check("源码有 GESTURE_WINDOW_MS", "GESTURE_WINDOW_MS" in text)
    check("源码有 on_single_click", "def on_single_click" in text)
    check("源码有 on_double_click", "def on_double_click" in text)
    check("源码有 on_triple_click", "def on_triple_click" in text)
    check("源码有 on_tap（计数与手势解耦）", "def on_tap" in text)
    check("源码不再有 on_multi_click", "def on_multi_click" not in text)
    check("源码不再有 STICKER_CLOSE_DELAY_MS",
          "STICKER_CLOSE_DELAY_MS" not in text)
    check("源码有 T_EXPR_HOLD", "T_EXPR_HOLD" in text)
    check("源码不再有 _schedule_sticker_close",
          "_schedule_sticker_close" not in text)
    # dblclick 分支里 Qt 仍会派发第 2 次点击的 release，
    # 不抑制就会把双击数成 3 次 -> 所以 _suppress_release 是必需的
    check("源码有 _suppress_release（双击去重）",
          "_suppress_release" in text)

    print()
    if FAILED:
        print("FAIL: %d 项未通过 -> %s" % (len(FAILED), FAILED))
        return 1
    print("PASS: 全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
