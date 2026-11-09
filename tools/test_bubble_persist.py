#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""test_bubble_persist.py — 气泡常驻回归测试。

复现并锁死用户报的 bug：
    「点击之后显示的那个东西，点一下就消失了，不会给你一直显示那个东西」

根因：fade_out() 每次都往 anim.finished 上 connect 一个 hide 的 lambda 且永不
disconnect；第二次 pop_in() 的动画一结束，旧的 hide lambda 就把刚弹出的气泡
又关掉。修复后：pop_in/fade_out 不再注册一次性回调，淡出后的隐藏统一由
_on_anim_done 负责。

跑法: python test_bubble_persist.py
"""
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass  # pythonw.exe 下 sys.stdout 是 None
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pet"))

from PySide6.QtCore import QCoreApplication, QEventLoop, QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from mimo_bubble import BubbleWindow  # noqa: E402

FAILS = []


def check(name, cond, extra=""):
    print("  [%s] %s %s" % ("PASS" if cond else "FAIL", name, extra))
    if not cond:
        FAILS.append(name)


def pump(ms=400):
    """跑事件循环让动画走完。"""
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def main():
    app = QApplication(sys.argv)
    b = BubbleWindow()
    b.set_content("✦ 待机中", [("额度剩余", "72%"), ("MiMo 连接", "已连接")],
                  subtitle="MiMo 桌面伙伴", footer="再点桌宠收起 · 右键更多")

    print("== 第一次弹出 ==")
    b.pop_in()
    pump()
    check("第一次弹出后可见", b.isVisible())
    check("alpha 到位", abs(b.alpha - 1.0) < 0.02, "alpha=%.3f" % b.alpha)

    print("== 淡出（9 秒定时器触发的那一步）==")
    b.fade_out()
    pump()
    check("淡出后隐藏", not b.isVisible())

    print("== 第二次弹出（旧版在这里会瞬间消失）==")
    b.pop_in()
    pump()
    check("第二次弹出后仍然可见", b.isVisible(),
          "可见=%s alpha=%.3f" % (b.isVisible(), b.alpha))
    check("第二次弹出 alpha 到位", abs(b.alpha - 1.0) < 0.02,
          "alpha=%.3f" % b.alpha)

    print("== 第三次弹出（已可见时重复点击）==")
    b.pop_in()
    pump()
    check("第三次弹出后仍然可见", b.isVisible(),
          "可见=%s alpha=%.3f" % (b.isVisible(), b.alpha))

    print("== 淡出 -> 弹出 -> 淡出 -> 弹出 反复 ==")
    for i in range(3):
        b.fade_out()
        pump()
        b.pop_in()
        pump()
        check("第 %d 轮往返后可见" % (i + 1), b.isVisible(),
              "可见=%s alpha=%.3f" % (b.isVisible(), b.alpha))

    print("== close_now ==")
    b.close_now()
    check("close_now 后隐藏", not b.isVisible())

    b.pop_in()
    pump()
    check("close_now 之后还能重新弹出", b.isVisible())

    print("\n结果: %s" % ("全部通过" if not FAILS else "失败 -> %s" % FAILS))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
