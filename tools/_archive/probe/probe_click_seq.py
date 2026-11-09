#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""probe_click_seq.py - 探测 Qt 在单击/双击/三击下实际派发的事件序列。

为什么要探：
    三击判定要数「一共来了几次按压」。
    如果第三次按压被 Qt 派发成 mouseDoubleClickEvent 而不是
    mousePressEvent，只统计 press 就会漏掉一次。
    Windows 的 dblclick 由窗口过程按时间+位置自己合成，
    PostMessage 走的也是同一条路径，所以这里用 PostMessage 探测即可。

用法:
    python tools/probe_click_seq.py
"""

import ctypes
import sys
import time
from ctypes import wintypes

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication, QWidget

WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202

user32 = ctypes.windll.user32
user32.PostMessageW.argtypes = [wintypes.HWND, ctypes.c_uint,
                                ctypes.c_ulonglong, ctypes.c_longlong]
user32.PostMessageW.restype = wintypes.BOOL

TITLE = "click seq probe"
EVENTS = []


def lparam(x, y):
    return (y << 16) | (x & 0xFFFF)


def find_win(title):
    out = []
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p,
                                     ctypes.c_void_p)

    def cb(h, _l):
        buf = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(h, buf, 256)
        if buf.value == title:
            out.append(int(h))
        return True

    user32.EnumWindows(WNDENUMPROC(cb), 0)
    return out[0] if out else None


class Probe(QWidget):
    def mousePressEvent(self, e):
        EVENTS.append(("press", time.time()))
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        EVENTS.append(("release", time.time()))
        super().mouseReleaseEvent(e)

    def mouseDoubleClickEvent(self, e):
        EVENTS.append(("dblclick", time.time()))
        super().mouseDoubleClickEvent(e)


def click(hwnd, gap=0.12, hold=0.04, label=""):
    ok1 = user32.PostMessageW(hwnd, WM_LBUTTONDOWN, 1, lparam(50, 50))
    ok2 = user32.PostMessageW(hwnd, WM_LBUTTONUP, 0, lparam(50, 50))
    if not (ok1 and ok2):
        print("   [投递失败] %s err=%s" % (label, ctypes.get_last_error()))
    if gap:
        time.sleep(gap)


def dump(label):
    print("\n== %s ==" % label)
    if not EVENTS:
        print("   (没有收到任何事件)")
    t0 = EVENTS[0][1] if EVENTS else 0
    for name, ts in EVENTS:
        print("   %-9s +%5.0f ms" % (name, (ts - t0) * 1000))
    EVENTS[:] = []


def main():
    app = QApplication(sys.argv)
    w = Probe()
    w.setWindowTitle(TITLE)
    # 和桌宠本体完全一样的窗口标志
    w.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool |
                     Qt.WindowDoesNotAcceptFocus)
    w.setAttribute(Qt.WA_TranslucentBackground, True)
    w.setAttribute(Qt.WA_ShowWithoutActivating, True)
    w.setFixedSize(200, 200)
    w.show()
    app.processEvents()

    hwnd_winid = int(w.winId())
    hwnd_enum = find_win(TITLE)
    print("winId()=%s  EnumWindows=%s" % (hex(hwnd_winid),
                                          hex(hwnd_enum) if hwnd_enum else None))
    target = hwnd_enum or hwnd_winid

    def run():
        print("--- 投递目标 %s ---" % hex(target))
        click(target, gap=0, label="single")
        time.sleep(0.6)
        dump("单击")

        click(target, label="d1")
        click(target, gap=0, label="d2")
        time.sleep(0.6)
        dump("双击")

        click(target, label="t1")
        click(target, label="t2")
        click(target, gap=0, label="t3")
        time.sleep(0.8)
        dump("三击（间隔 120ms）")

        click(target, label="s1")
        click(target, label="s2")
        time.sleep(0.4)
        click(target, gap=0, label="s3")
        time.sleep(0.8)
        dump("双击 + 400ms 后第三次")

        app.quit()

    QTimer.singleShot(600, run)
    app.exec()
    return 0


if __name__ == "__main__":
    sys.exit(main())
