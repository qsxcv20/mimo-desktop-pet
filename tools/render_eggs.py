#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
render_eggs.py — 渲染所有彩蛋贴纸气泡 + 一张汇总图。

不进入事件循环，直接用 BubbleWindow 的贴纸模式渲染，
用来验收：排版、圆角裁切、描边、字号、尾巴位置。

用法：
    python tools/render_eggs.py
"""

import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass  # pythonw.exe 下 sys.stdout 是 None

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "pet"))

from PySide6.QtCore import Qt                            # noqa: E402
from PySide6.QtGui import QColor, QFont, QPainter        # noqa: E402
from PySide6.QtWidgets import QApplication              # noqa: E402

from mimo_bubble import BubbleWindow                    # noqa: E402
from mimo_egg import EggTracker                         # noqa: E402

OUT = os.path.join(ROOT, "_mimo", "eggs")
STATE_EMOJI = {"idle": "✦", "happy": "★", "think": "…", "tired": "✖"}
STATE_LABEL = {"idle": "待机中", "happy": "任务完成啦！",
               "think": "正在思考…", "tired": "出错了 / 等授权中"}


def main():
    os.makedirs(OUT, exist_ok=True)
    app = QApplication(sys.argv)

    t = EggTracker()
    if not len(t.pack):
        print("没有找到贴纸素材")
        return 2

    shots = []
    for item in t.pack.items:
        b = BubbleWindow()
        pm = t.pack.pixmap(item)
        mood = item.get("mood", "idle")
        sub = "%s %s" % (STATE_EMOJI.get(mood, "✦"),
                         STATE_LABEL.get(mood, mood))
        b.set_sticker(pm, title="", sub=sub,
                      footer="再点桌宠收起 · 5 秒后自动收起",
                      dark=bool(item.get("dark")))
        b.pop_in()
        b.setAlpha(1.0)
        app.processEvents()
        path = os.path.join(OUT, item["file"].replace(".png", "-bubble.png"))
        b.grab().save(path)
        print("  %-14s %-14s -> %s (%dx%d)"
              % (item["file"], item["label"], path, b.width(), b.height()))
        shots.append((item, path))
        b.close_now()

    # 汇总图：把 9 张气泡排成 3x3
    imgs = []
    for item, path in shots:
        from PySide6.QtGui import QPixmap
        imgs.append(QPixmap(path))
    cols = 3
    rows = (len(imgs) + cols - 1) // cols
    cw = max(p.width() for p in imgs) + 16
    ch = max(p.height() for p in imgs) + 16
    W, H = cw * cols, ch * rows
    from PySide6.QtGui import QPixmap as QP
    sheet = QP(W, H)
    sheet.fill(QColor(246, 240, 232))
    p = QPainter(sheet)
    for i, pm in enumerate(imgs):
        r, c = divmod(i, cols)
        p.drawPixmap(c * cw + 8, r * ch + 8, pm)
    p.end()
    sheet_path = os.path.join(OUT, "all-eggs.png")
    sheet.save(sheet_path)
    print("\n汇总 -> %s (%dx%d)" % (sheet_path, W, H))
    return 0


if __name__ == "__main__":
    sys.exit(main())
