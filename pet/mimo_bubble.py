#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
mimo_bubble.py — 桌宠气泡对话框（QPainter 手绘，橙/白/黑三色）。

风格参考 DSH 系桌宠（whale-musume / dsh-pet）：
  * 圆角 13px，padding 14×11
  * 弹出用 cubic-bezier(.34,1.4,.64,1) 的过冲感（这里用 QPropertyAnimation + OutBack）
  * 尾巴是从主体边缘长出来的小三角，根部被主体描边盖住，视觉上无缝
  * 不硬编码深浅：气泡永远用暖白底 + 橙边，压在 MiMo 深色 UI 上也清晰

气泡是独立的顶层窗口（owner = MiMo 主窗口），
所以它会跟着 MiMo 一起被别的窗口盖住，位置也不会超出 MiMo 客户区。

绘制顺序（关键）：影子 -> 尾巴填充 -> 主体 -> 尾巴外沿描边。
尾巴几何必须整体落在主体轮廓之外，否则会被主体完全盖住。
"""

import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass  # pythonw.exe 下 sys.stdout 是 None

from PySide6.QtCore import (QEasingCurve, QPointF, Property, QPropertyAnimation,
                            QRectF, Qt, QTimer)
from PySide6.QtGui import (QColor, QFont, QFontMetrics, QLinearGradient, QPainter,
                           QPainterPath, QPen, QPixmap)
from PySide6.QtWidgets import QWidget

# ---- 配色（严格橙/白/黑）----
C_ORANGE = QColor(242, 122, 26)
C_ORANGE_D = QColor(196, 88, 10)
C_ORANGE_L = QColor(255, 176, 92)
C_CREAM = QColor(255, 252, 246)
C_INK = QColor(32, 24, 18)
C_INK_L = QColor(122, 104, 90)
C_WHITE = QColor(255, 255, 255)
C_WARN = QColor(206, 66, 52)

# 深色气泡（配深色底贴纸）
C_DARK_1 = QColor(74, 60, 56)
C_DARK_2 = QColor(52, 42, 40)
C_DARK_TXT = QColor(245, 236, 228)
C_DARK_SUB = QColor(255, 186, 110)

RADIUS = 13
PAD_X = 14
PAD_Y = 11
TAIL_LEN = 11        # 尾巴从主体边缘伸出的长度
TAIL_HW = 7.0        # 尾巴根部半宽

STICKER_MAX = 200    # 贴纸在气泡里显示的最大边长
STICKER_RADIUS = 8   # 贴纸圆角


class BubbleWindow(QWidget):
    """桌宠气泡。内容 = 标题 + 若干 (label, value) 行 + 可选进度条。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("MiMo 桌宠气泡")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool |
                            Qt.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        # 气泡是纯信息层：鼠标穿透到下面的 MiMo，不会挡住用户操作，
        # 也不会因为「点一下」就把自己关掉。
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setFocusPolicy(Qt.NoFocus)

        self._title = "MiMo"
        self._subtitle = ""
        self._rows = []          # [(label, value)]
        self._bar = None         # (percent, color)
        self._footer = ""
        self._tail_side = "bottom"
        self._tail_x = 0.5       # 0..1，气泡内尾部的横向位置
        self._visible_anim = None
        self._alpha = 0.0
        self._fade_done = None
        # 贴纸模式：显示一张表情包图片（彩蛋）
        self._sticker = None     # QPixmap
        self._sticker_title = ""
        self._sticker_sub = ""
        self._sticker_dark = False

        self._resize_to_content()
        self._anim = QPropertyAnimation(self, b"alpha", self)
        self._anim.setDuration(220)
        self._anim.setEasingCurve(QEasingCurve.OutBack)   # 过冲 -> 可爱
        self._anim.finished.connect(self._on_anim_done)

    # ---- 内容 ----

    def alpha(self):
        return self._alpha

    def setAlpha(self, v):
        self._alpha = float(v)
        self.update()

    alpha = Property(float, alpha, setAlpha)

    def set_content(self, title, rows, subtitle="", bar=None, footer="",
                    tail_side="bottom", tail_x=0.5):
        self._sticker = None
        self._title = title
        self._subtitle = subtitle
        self._rows = list(rows or [])
        self._bar = bar
        self._footer = footer
        self._tail_side = tail_side
        self._tail_x = tail_x
        self._resize_to_content()
        self.update()

    def set_sticker(self, pixmap, title="", sub="", footer="",
                    tail_side="bottom", tail_x=0.5, dark=False):
        """贴纸模式：显示一张表情包图片（彩蛋）。

        图片按 STICKER_MAX 等比缩放后居中放在气泡里，带圆角裁切 +
        细描边，读起来像一张「卡片」。气泡外壳、尾巴、动画和普通气泡
        完全一致，所以 owner 绑定 / 自动收起 / 再点收起都不用改。

        dark=True 时气泡整体转深色（配深色底贴纸），
        免得白气泡套深色图显得割裂。
        """
        self._sticker = pixmap
        self._sticker_dark = bool(dark)
        self._title = ""
        self._subtitle = ""
        self._rows = []
        self._bar = None
        self._sticker_title = title
        self._sticker_sub = sub
        self._footer = footer
        self._tail_side = tail_side
        self._tail_x = tail_x
        self._resize_to_content()
        self.update()

    def set_tail(self, side, tail_x=0.5):
        """只改尾巴方向/位置（气泡摆位后会调用）。"""
        side = side if side in ("bottom", "top", "left", "right") else "bottom"
        tx = max(0.08, min(0.92, float(tail_x)))
        if side == self._tail_side and abs(tx - self._tail_x) < 0.01:
            return
        self._tail_side = side
        self._tail_x = tx
        self._resize_to_content()
        self.update()

    def tail_side(self):
        return self._tail_side

    # ---- 尺寸 ----

    def _tail_margin(self):
        """尾巴需要额外预留的空间 (left, top, right, bottom)。"""
        if self._tail_side == "bottom":
            return (0, 0, 0, TAIL_LEN + 3)
        if self._tail_side == "top":
            return (0, TAIL_LEN + 3, 0, 0)
        if self._tail_side == "left":
            return (TAIL_LEN + 3, 0, 0, 0)
        if self._tail_side == "right":
            return (0, 0, TAIL_LEN + 3, 0)
        return (0, 0, 0, 0)

    def _resize_to_content(self):
        if self._sticker is not None:
            return self._resize_sticker()
        f = QFont("Microsoft YaHei UI", 9)
        fb = QFont("Microsoft YaHei UI", 10)
        fb.setBold(True)
        fm = QFontMetrics(f)
        w = 0
        if self._title:
            w = max(w, QFontMetrics(fb).horizontalAdvance(self._title))
        if self._subtitle:
            w = max(w, fm.horizontalAdvance(self._subtitle))
        for label, value in self._rows:
            w = max(w, fm.horizontalAdvance(label) + 20 +
                    fm.horizontalAdvance(str(value)))
        if self._footer:
            w = max(w, fm.horizontalAdvance(self._footer))
        w = max(w, 186)

        h = PAD_Y * 2
        if self._title:
            h += 20
        if self._subtitle:
            h += 16
        for _ in self._rows:
            h += 21
        if self._bar:
            h += 18
        if self._footer:
            h += 16

        ml, mt, mr, mb = self._tail_margin()
        self.setFixedSize(int(w + PAD_X * 2 + ml + mr),
                          int(h + mt + mb))

    def _resize_sticker(self):
        """贴纸模式的尺寸：图片等比缩到 STICKER_MAX，下方带标题/副标题/脚注。"""
        pm = self._sticker
        iw, ih = pm.width(), pm.height()
        if iw <= 0 or ih <= 0:
            iw = ih = STICKER_MAX
        scale = min(1.0, float(STICKER_MAX) / max(iw, ih))
        dw, dh = int(iw * scale), int(ih * scale)

        fb = QFont("Microsoft YaHei UI", 10)
        fb.setBold(True)
        f = QFont("Microsoft YaHei UI", 9)
        fm = QFontMetrics(f)
        fmb = QFontMetrics(fb)

        w = dw
        if self._sticker_title:
            w = max(w, fmb.horizontalAdvance(self._sticker_title))
        if self._sticker_sub:
            w = max(w, fm.horizontalAdvance(self._sticker_sub))
        if self._footer:
            w = max(w, fm.horizontalAdvance(self._footer))
        w = max(w, 200)

        h = dh
        if self._sticker_title:
            h += 22
        if self._sticker_sub:
            h += 17
        if self._footer:
            h += 17

        ml, mt, mr, mb = self._tail_margin()
        self.setFixedSize(int(w + PAD_X * 2 + ml + mr),
                          int(h + PAD_Y * 2 + mt + mb))

    def _body_rect(self):
        """主体矩形（已排除尾巴占位）。"""
        ml, mt, mr, mb = self._tail_margin()
        return QRectF(1.5 + ml, 1.5 + mt,
                      self.width() - 3 - ml - mr,
                      self.height() - 3 - mt - mb)

    # ---- 显示 / 隐藏 ----

    def pop_in(self):
        """弹出。只启动动画，不注册任何一次性回调。

        注意：这里绝不能再 connect(finished, hide) —— 旧版每次 fade_out 都往
        finished 上挂一个 hide 的 lambda，且永不 disconnect。结果就是第二次
        点击弹出时，动画一结束就把刚弹出的气泡又关掉（用户看到的
        「点一下就消失」）。淡出后的隐藏统一由 _on_anim_done 负责。
        """
        self._fade_done = None
        self._anim.stop()
        self.show()
        self.raise_()
        self._anim.setEasingCurve(QEasingCurve.OutBack)
        self._anim.setStartValue(self._alpha)
        self._anim.setEndValue(1.0)
        self._anim.start()

    def fade_out(self, done=None):
        self._fade_done = done
        self._anim.stop()
        self._anim.setStartValue(self._alpha)
        self._anim.setEndValue(0.0)
        self._anim.setEasingCurve(QEasingCurve.InQuad)
        self._anim.start()

    def close_now(self):
        """立刻隐藏（不等动画）。"""
        self._anim.stop()
        self._alpha = 0.0
        self.hide()

    def _on_anim_done(self):
        if self._alpha <= 0.01:
            self.hide()
            cb = self._fade_done
            self._fade_done = None
            if cb:
                cb()

    # ---- 交互 ----

    def mousePressEvent(self, event):
        """气泡是纯信息的：点击不关闭、也不吃掉点击（穿透给 MiMo）。

        用户明确要求「点了不要马上消失、要一直显示」，所以这里不做任何关闭动作。
        """
        event.ignore()

    # ---- 绘制 ----

    def paintEvent(self, e):
        if self._alpha <= 0.01:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        p.setOpacity(self._alpha)

        body = self._body_rect()

        # 影子（多层递减 alpha 模拟柔化）
        for i in range(6, 0, -1):
            a = int(9 * (1.0 - i / 7.0))
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(0, 0, 0, a))
            p.drawRoundedRect(body.adjusted(-i * 0.5, -i * 0.4 + i * 0.9,
                                            i * 0.5, i * 0.7 + i * 0.9),
                              RADIUS + i, RADIUS + i)

        # 尾巴：先填充（整体在主体轮廓之外），主体画在上面会盖住根部
        self._fill_tail(p, body)

        # 主体
        dark = self._sticker is not None and self._sticker_dark
        if dark:
            grad = QLinearGradient(body.topLeft(), body.bottomLeft())
            grad.setColorAt(0.0, C_DARK_1)
            grad.setColorAt(1.0, C_DARK_2)
        else:
            grad = QLinearGradient(body.topLeft(), body.bottomLeft())
            grad.setColorAt(0.0, C_WHITE)
            grad.setColorAt(1.0, C_CREAM)
        p.setBrush(grad)
        p.setPen(QPen(C_ORANGE, 2))
        p.drawRoundedRect(body, RADIUS, RADIUS)

        # 尾巴外沿描边（根部那条边被主体描边自然盖住）
        self._stroke_tail(p, body)

        # 内容
        if self._sticker is not None:
            self._paint_sticker(p, body)
            return

        x = PAD_X + body.left() - 1.5
        y = PAD_Y + body.top() - 1.5
        fb = QFont("Microsoft YaHei UI", 10)
        fb.setBold(True)
        f = QFont("Microsoft YaHei UI", 9)

        if self._title:
            p.setFont(fb)
            p.setPen(QPen(C_INK))
            p.drawText(x, y + 13, self._title)
            y += 20
            if self._subtitle:
                p.setFont(f)
                p.setPen(QPen(C_ORANGE_D))
                p.drawText(x, y + 12, self._subtitle)
                y += 16
        elif self._subtitle:
            p.setFont(f)
            p.setPen(QPen(C_ORANGE_D))
            p.drawText(x, y + 12, self._subtitle)
            y += 16

        for label, value in self._rows:
            p.setFont(f)
            p.setPen(QPen(C_INK_L))
            p.drawText(x, y + 14, str(label))
            p.setPen(QPen(C_INK))
            p.drawText(x + self._content_w() - p.fontMetrics().horizontalAdvance(str(value)),
                       y + 14, str(value))
            y += 21

        if self._bar:
            pct, col = self._bar
            pct = max(0.0, min(1.0, float(pct)))
            barw = self._content_w()
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(0, 0, 0, 28))
            p.drawRoundedRect(QRectF(x, y + 4, barw, 8), 4, 4)
            c = col if isinstance(col, QColor) else C_ORANGE
            p.setBrush(c)
            p.drawRoundedRect(QRectF(x, y + 4, max(6.0, barw * pct), 8), 4, 4)
            y += 18

        if self._footer:
            p.setFont(f)
            p.setPen(QPen(C_INK_L))
            p.drawText(x, y + 12, self._footer)
            y += 16

        # 标题右侧的小圆点（状态灯）
        if self._title:
            p.setPen(Qt.NoPen)
            p.setBrush(C_ORANGE)
            p.drawEllipse(QRectF(x + self._content_w() - 7, y - 30, 7, 7))

    def _paint_sticker(self, p, body):
        """贴纸模式绘制：图片（圆角裁切 + 细描边）+ 标题/副标题/脚注。"""
        pm = self._sticker
        iw, ih = pm.width(), pm.height()
        if iw <= 0 or ih <= 0:
            return
        scale = min(1.0, float(STICKER_MAX) / max(iw, ih))
        dw, dh = int(iw * scale), int(ih * scale)

        x = body.left() + (body.width() - dw) / 2.0
        y = body.top() + PAD_Y - 1.5
        rect = QRectF(x, y, dw, dh)

        # 图片本体：圆角裁切
        clip = QPainterPath()
        clip.addRoundedRect(rect, STICKER_RADIUS, STICKER_RADIUS)
        p.save()
        p.setClipPath(clip)
        p.drawPixmap(rect, pm, QRectF(0, 0, iw, ih))
        p.restore()

        # 细描边（深棕，和整体描边风格一致）
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(90, 62, 44, 90), 1))
        p.drawRoundedRect(rect, STICKER_RADIUS, STICKER_RADIUS)

        y += dh + 4

        sub_col = C_DARK_SUB if self._sticker_dark else C_ORANGE_D
        foot_col = C_DARK_TXT if self._sticker_dark else C_INK_L

        if self._sticker_title:
            fb = QFont("Microsoft YaHei UI", 10)
            fb.setBold(True)
            p.setFont(fb)
            p.setPen(QPen(C_DARK_TXT if self._sticker_dark else C_INK))
            tw = p.fontMetrics().horizontalAdvance(self._sticker_title)
            p.drawText(body.left() + (body.width() - tw) / 2.0, y + 14,
                       self._sticker_title)
            y += 22

        if self._sticker_sub:
            f = QFont("Microsoft YaHei UI", 9)
            p.setFont(f)
            p.setPen(QPen(sub_col))
            sw = p.fontMetrics().horizontalAdvance(self._sticker_sub)
            p.drawText(body.left() + (body.width() - sw) / 2.0, y + 12,
                       self._sticker_sub)
            y += 17

        if self._footer:
            f = QFont("Microsoft YaHei UI", 9)
            p.setFont(f)
            p.setPen(QPen(foot_col))
            fw = p.fontMetrics().horizontalAdvance(self._footer)
            p.drawText(body.left() + (body.width() - fw) / 2.0, y + 12,
                       self._footer)

    def _content_w(self):
        body = self._body_rect()
        return body.width() - PAD_X * 2

    # ---- 尾巴几何 ----

    def _tail_geo(self, body):
        """返回 (ax, ay, bx, by, cx, cy)：A/B 是根部两点，C 是尖端。"""
        if self._tail_side == "bottom":
            cx = body.left() + self._tail_x * body.width()
            y0 = body.bottom() - 1.0
            return (cx - TAIL_HW, y0, cx + TAIL_HW, y0, cx, y0 + TAIL_LEN)
        if self._tail_side == "top":
            cx = body.left() + self._tail_x * body.width()
            y0 = body.top() + 1.0
            return (cx - TAIL_HW, y0, cx + TAIL_HW, y0, cx, y0 - TAIL_LEN)
        if self._tail_side == "left":
            cy = body.top() + (1.0 - self._tail_x) * body.height()
            x0 = body.left() + 1.0
            return (x0, cy - TAIL_HW, x0, cy + TAIL_HW, x0 - TAIL_LEN, cy)
        cy = body.top() + (1.0 - self._tail_x) * body.height()
        x0 = body.right() - 1.0
        return (x0, cy - TAIL_HW, x0, cy + TAIL_HW, x0 + TAIL_LEN, cy)

    def _fill_tail(self, p, body):
        ax, ay, bx, by, cx, cy = self._tail_geo(body)
        tri = QPainterPath()
        tri.moveTo(ax, ay)
        tri.lineTo(bx, by)
        tri.lineTo(cx, cy)
        tri.closeSubpath()
        p.setPen(Qt.NoPen)
        if self._sticker is not None and self._sticker_dark:
            p.setBrush(C_DARK_1)
        else:
            p.setBrush(C_CREAM)
        p.drawPath(tri)

    def _stroke_tail(self, p, body):
        """只描两条外沿斜边；根部那条被主体描边盖住。"""
        ax, ay, bx, by, cx, cy = self._tail_geo(body)
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(C_ORANGE, 2, Qt.SolidLine, Qt.RoundCap,
                      Qt.MiterJoin))
        p.drawLine(QPointF(ax, ay), QPointF(cx, cy))
        p.drawLine(QPointF(cx, cy), QPointF(bx, by))


def place_bubble(bubble, pet_x, pet_y, pet_w, pet_h, host_x, host_y,
                 host_w, host_h, gap=8):
    """把气泡摆到桌宠旁边，并夹在宿主客户区内。

    返回 (x, y, tail_side, tail_x)：
        tail_side 指示尾巴朝哪边，才能指着桌宠
        tail_x    是尾巴在气泡宽度里的相对位置（0..1）
    """
    bw, bh = bubble.width(), bubble.height()
    above = True
    y = pet_y - bh - gap
    if y < host_y + 4:
        y = pet_y + pet_h + gap
        above = False
    if y + bh > host_y + host_h - 4:
        y = host_y + host_h - bh - 4
        above = False
    x = pet_x + (pet_w - bw) / 2.0
    x = max(host_x + 4, min(x, host_x + host_w - bw - 4))
    y = max(host_y + 4, min(y, host_y + host_h - bh - 4))

    # 尾巴对准桌宠中心
    pet_cx = pet_x + pet_w / 2.0
    tail_x = (pet_cx - x) / float(max(1, bw))
    tail_x = max(0.10, min(0.90, tail_x))
    side = "bottom" if above else "top"
    return int(x), int(y), side, tail_x
