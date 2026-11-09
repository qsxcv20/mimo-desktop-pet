#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
mimo_pet.py — MiMo 桌面伙伴（住在 MiMo 应用窗口里面）

载体方案（不改 MiMo 任何文件，避开 runtime-res 的 sha256 校验）：
    把桌宠窗口的 GWLP_HWNDPARENT 设成 MiMo 主窗口句柄 -> 变成「owned window」。
    Windows 语义：owned window 永远在 owner 之上；owner 最小化/隐藏时一起隐藏；
    owner 被别的窗口压住时桌宠跟着被压住。
    再配合「用 MiMo 客户区坐标定位 + 每帧同步屏幕位置」，
    桌宠在几何上被严格限制在 MiMo 窗口内部。

功能：
    * 自动贴边：拖拽松手吸附到最近的边/角；空闲时会自己溜达去别的角
    * 点击弹气泡：显示 MiMo 当前状态 + 小米额度/用量
    * 状态驱动：订阅 MiMo 本地 API /v1/sessions/<id>/events (SSE)
        busy / text-partial  -> think
        ui(usage) / busy 后   -> happy（短暂）
        ui(kind=error)        -> tired
    * 托盘常驻 + 右键菜单 + MiMo skill / CLI 远程控制

用法：
    python mimo_pet.py
    python mimo_pet.py --selftest
"""

import json
import math
import os
import random
import sys
import threading
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass  # pythonw.exe 下 sys.stdout 是 None

from PySide6.QtCore import Qt, QTimer, QPoint, QPointF, QRect, QRectF, QSize
from PySide6.QtGui import (QAction, QColor, QCursor, QFont, QIcon, QImage,
                           QPainter, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QMenu, QMessageBox,
                               QSystemTrayIcon, QWidget)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mimo_host as H                                      # noqa: E402
from mimo_bubble import BubbleWindow, place_bubble         # noqa: E402
from mimo_egg import EggTracker                           # noqa: E402
from mimo_link import MimoClient, MimoListener, PetBrain   # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG = os.path.join(HERE, "pet_config.json")
DEFAULT_SPRITE_DIR = r"D:\桌面宠物\build\mimo-witch"

# 「用户主动关掉了桌宠」标记文件。
# 没有它的话，watchdog（每 10 秒）和计划任务（每 1 分钟）会把桌宠
# 无限拉回来，用户点右键「退出」等于没点。
DISABLED_FILE = os.path.join(HERE, "pet_disabled")

MIMO_EXE = os.path.join(
    os.environ.get("LOCALAPPDATA", ""), "Programs", "Xiaomi MiMo",
    "Xiaomi MiMo.exe")
# 额度读取靠 CDP 调 MiMo 自己的 window.mimo.getUserUsage()，
# 所以 MiMo 必须带 --remote-debugging-port 启动（只监听 127.0.0.1）
CDP_PORT = int(os.environ.get("MIMO_CDP_PORT", "9333"))

DEFAULT_CFG = {
    "sprite_dir": DEFAULT_SPRITE_DIR,
    "size": 220,            # 桌宠显示边长（像素）
    "host_mode": "owner",   # owner = 绑定到 MiMo 窗口内部
    "layout_version": 2,    # 坐标语义从「屏幕」变成「MiMo 客户区」，变了就重置位置
    "snap": True,           # 拖拽松手自动贴边
    "wander": True,         # 空闲自动溜达
    "follow_mimo": True,    # 跟随 MiMo 任务状态
    "launch_mimo": False,   # 桌宠**不再**主动把 MiMo 带起来（联动模式下 MiMo 才是主）
    "link_mimo": True,     # 联动：MiMo 开 -> 桌宠自动唤醒；MiMo 关 -> 桌宠自动退出
    "exit_grace": 8.0,     # 找不到 MiMo 多少秒后退出（给 MiMo 冷启动留宽限）
    "show_balloon": True,
    # 气泡自动收起秒数。用户要求「4~5 秒刚好够看完信息」，
    # 所以默认 5 秒；点桌宠也可以随时手动收起。
    # 设成 0 = 永不自动收起。
    "bubble_timeout": 5,
    "click_through": False,
    "start_minimized": False,
    "x": None,              # 客户区坐标
    "y": None,
    "corner": "br",         # 记忆的角落
}

STATE_LABEL = {
    "idle":  "待机中",
    "happy": "任务完成啦！",
    "think": "正在思考…",
    "tired": "出错了 / 等授权中",
}

STATE_EMOJI = {
    "idle": "✦", "happy": "★", "think": "…", "tired": "✖",
}

C_ORANGE = QColor(242, 122, 26)

# Windows class style: CS_DBLCLKS
#
# 关键坑（本轮实机发现）：Qt 的 QWidget 顶层窗口默认**不带**
# CS_DBLCLKS。Windows 只有在窗口 class 带这个标志时，
# 才会把「第 2 次按下」合成成 WM_LBUTTONDBLCLK ——
# 也就是说，没有它，mouseDoubleClickEvent 永远不会触发，
# 双击功能等于不存在。
#
# Qt 没有暴露这个标志，只能用 SetClassLongPtr 手动补。
# 注意：要在窗口**创建之后**才生效，而且作用在 Qt 为这个窗口
# 注册的 class 上（同一个 class 可能被多个窗口共用）。
CS_DBLCLKS = 0x0008
GCL_STYLE = -26        # GetClassLongPtr 的 index

# 手势仲裁的时间参数（PetWindow 和 Controller 共用）
#   GESTURE_WAIT_MS  = 单击挂起多久（等 dblclick 跟上来）
#   TRIPLE_WAIT_MS   = 双击后再等多久（看有没有第三次点击）
#   GESTURE_WINDOW_MS = 连点间隔超过这个就断开计数
GESTURE_WAIT_MS = 500
TRIPLE_WAIT_MS = 260
GESTURE_WINDOW_MS = 700


# ---------------------------------------------------------------- 小工具

def _quota_error_text(err):
    """把底层报错翻译成一句人话。"""
    s = str(err or "")
    if "调试端口" in s:
        return "需用调试端口启动 MiMo"
    if "无有效订阅" in s or "已到期" in s:
        return "套餐已到期"
    if "未返回额度" in s or "账号可能未登录" in s:
        return "小米账号未登录"
    if "70016" in s or "会话已过期" in s:
        return "小米账号会话已过期"
    if "未取得小米账号会话" in s or "没有小米账号会话" in s:
        return "需要小米账号会话"
    if "401" in s or "过期" in s or "重新登录" in s:
        return "账号会话已过期"
    if "loginUrl" in s:
        return "账号未授权"
    if "cookie" in s.lower() or "Errno 13" in s or "WinError 32" in s:
        return "cookie 被占用"
    if "urlopen" in s.lower() or "timed out" in s.lower() or "网络" in s:
        return "网络不通"
    return (s[:16] + "…") if len(s) > 16 else (s or "未知错误")


PLAN_STATUS = {
    "ACTIVE": "生效中",
    "EXPIRED": "已到期",
    "CANCELLED": "已取消",
    "PENDING": "待生效",
    "SUSPENDED": "已暂停",
    "REFUNDED": "已退款",
}


def _short_date(s):
    """日期 -> '11-01'

    能处理三种写法：
        '2026-11-11 23:59:59'   （MiMo 自己的 resetDate）
        '2026-11-01T14:16:35Z'  （订阅接口的 ISO 8601）
        '2026-11-01T14:16:35+08:00'
    带 Z 的按 UTC 转成本地时间再显示。
    """
    if not s:
        return ""
    txt = str(s).strip()
    try:
        import datetime as dt
        body = txt.replace("T", " ")
        utc = body.endswith("Z")
        if utc:
            body = body[:-1].strip()
        # 去掉 +08:00 / -05:00 这种时区偏移
        tail = body[10:]
        for sign in ("+", "-"):
            if sign in tail:
                body = body[:10] + tail.split(sign)[0]
                break
        body = body.strip()
        if len(body) <= 10:
            d = dt.datetime.strptime(body, "%Y-%m-%d")
        else:
            d = dt.datetime.strptime(body[:19], "%Y-%m-%d %H:%M:%S")
        if utc:
            d = d.replace(tzinfo=dt.timezone.utc).astimezone()
        return d.strftime("%m-%d")
    except Exception:
        pass
    try:
        ymd = txt.split()[0].split("-")
        return "%s-%s" % (ymd[1], ymd[2])
    except Exception:
        return txt[:10]


def _fmt_num(n):
    """1234567 -> '1.23M'"""
    try:
        n = float(n)
    except Exception:
        return str(n)
    if n >= 1e8:
        return "%.2f亿" % (n / 1e8)
    if n >= 1e4:
        return "%.1fK" % (n / 1e3)
    return "%d" % n


_TOKEN_KEYS = ("totalToken", "totalTokens", "total_tokens",
               "tokenUsage", "tokens", "tokenCount", "usage")
_TOKEN_FIELDS = ("totalTokens", "totalToken", "tokens", "tokenCount",
                 "inputTokens", "outputTokens", "promptTokens",
                 "completionTokens")


def _extract_tokens(obj, depth=0):
    """从 usage 事件里递归找 token 数字（字段名可能变，做容错）。"""
    if depth > 6:
        return 0
    if isinstance(obj, (int, float)):
        return int(obj)
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in _TOKEN_FIELDS and isinstance(v, (int, float)):
                return int(v)
        for k, v in obj.items():
            if any(t.lower() in str(k).lower() for t in _TOKEN_KEYS):
                n = _extract_tokens(v, depth + 1)
                if n:
                    return n
        for v in obj.values():
            n = _extract_tokens(v, depth + 1)
            if n:
                return n
    elif isinstance(obj, list):
        for v in obj:
            n = _extract_tokens(v, depth + 1)
            if n:
                return n
    return 0


# ---------------------------------------------------------------- 素材

class SpriteSheet(object):
    """读取 manifest.json + spritesheet.webp，切出每个动画的帧。"""

    def __init__(self, sprite_dir):
        self.dir = sprite_dir
        mf = os.path.join(sprite_dir, "manifest.json")
        if not os.path.isfile(mf):
            raise RuntimeError("缺少 manifest.json: " + mf)
        with open(mf, "r", encoding="utf-8") as f:
            self.manifest = json.load(f)

        sheet_name = self.manifest.get("spritesheet", "spritesheet.webp")
        sheet_path = os.path.join(sprite_dir, sheet_name)
        if not os.path.isfile(sheet_path):
            raise RuntimeError("缺少精灵图: " + sheet_path)

        from PIL import Image
        im = Image.open(sheet_path).convert("RGBA")
        buf = im.tobytes()
        qimg = QImage(buf, im.width, im.height, QImage.Format_RGBA8888).copy()
        self.sheet = QPixmap.fromImage(qimg)

        self.fw = int(self.manifest["frameWidth"])
        self.fh = int(self.manifest["frameHeight"])
        self.cols = int(self.manifest["columns"])
        self.animations = self.manifest.get("animations") or {}
        if "idle" not in self.animations:
            raise RuntimeError("manifest 缺少 idle 动画")

        self.frames = {}
        self.meta = {}
        for name, a in self.animations.items():
            row = int(a["row"])
            n = int(a["frames"])
            frames = []
            for i in range(n):
                idx = row * self.cols + i      # row-major，跨行续排
                r, c = divmod(idx, self.cols)
                if (r + 1) * self.fh > self.sheet.height():
                    break
                frames.append(self.sheet.copy(QRect(c * self.fw, r * self.fh,
                                                    self.fw, self.fh)))
            if not frames:
                continue
            self.frames[name] = frames
            self.meta[name] = {"fps": int(a.get("fps", 8)),
                               "loop": bool(a.get("loop", True))}
        if "idle" not in self.frames:
            raise RuntimeError("精灵图里没有 idle 帧")

    def has(self, name):
        return name in self.frames

    def frame(self, name, index):
        frames = self.frames.get(name) or self.frames["idle"]
        return frames[index % len(frames)]


# ---------------------------------------------------------------- 桌宠窗口

class PetWindow(QWidget):
    """透明无边框的桌宠本体。位置由 Controller 按 MiMo 客户区坐标控制。"""

    def __init__(self, sprites, controller):
        super().__init__()
        self.sprites = sprites
        self.controller = controller
        self.drag_offset = None
        self.press_pos = None
        self.moved = False
        self._frame_index = 0
        self._current = "idle"
        self._flip = False
        self._squash = 0.0          # >0 纵向压扁（点击反馈）
        self._glow = 0.0            # 忙碌时的橙色光晕

        self.setWindowTitle("MiMo 桌宠")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool |
                            Qt.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setFixedSize(self.controller.pet_size, self.controller.pet_size)
        self.setCursor(QCursor(Qt.OpenHandCursor))
        self._ensure_dblclks()

        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._advance)
        self.anim_timer.start(self._interval("idle"))

        # 单击 / 双击 / 三击判定（手势仲裁）
        #
        # 2026-11-09 新规则（用户定）：
        #     单击 = 额度气泡（贴纸亮着时单击 = 切回额度气泡去「查看」）
        #     双击 = 表情包贴纸
        #     三击 = 只换表情（临时），不再弹贴纸
        #
        # Qt / Windows 的真实事件序列（很关键，别凭直觉写）：
        #     单击：press → release
        #     双击：press → release → dblclick → release
        #           Windows 把第 2 次「按下」换成 WM_LBUTTONDBLCLK，
        #           所以 dblclick 代表「第 2 次点击」，
        #           它后面那个 release 是第 2 次点击的松手。
        #     三击：press → release → dblclick → release → press → release
        #           第 3 次点击又是普通的 press/release。
        #     四击：… → press → release → dblclick → release
        #
        # 坑（本轮实测踩到）：
        #     如果把 dblclick 当成「额外的一次点击」再加一个 release，
        #     双击会被数成 3 次 -> 直接判成三击。
        #     正确做法：dblclick **不计数**，它只是把「当前这一串」
        #     的语义标记成「至少 2 次」。
        self._clicks = 0                  # 这一串里数到的点击次数
        self._suppress_release = False    # dblclick 后面那个 release 不再计数
        self._last_click_at = 0.0         # 上一次点击时间（判断是否同一串）
        self._gesture_timer = QTimer(self)
        self._gesture_timer.setSingleShot(True)
        self._gesture_timer.timeout.connect(self._on_gesture_timeout)

    def _ensure_dblclks(self):
        """给窗口 class 补上 CS_DBLCLKS，让 Windows 合成双击事件。

        坑（本轮实机发现，很重要）：
            Qt 的 QWidget 顶层窗口默认**不带** CS_DBLCLKS。
            Windows 只在窗口 class 带这个标志时，才会把「第 2 次按下」
            合成成 WM_LBUTTONDBLCLK。
            没有它 -> mouseDoubleClickEvent 永远不触发 ->
            「双击出贴纸」这个功能等于从来没生效过。
            （之前测试用 PostMessage 注入，绕过了 Windows 的合成，
              所以一直没暴露出来。）

        实现要点：
            * 必须在窗口**创建之后**调用（winId() 之后）
            * 改的是 class style，作用在该 class 的所有窗口上
              —— Qt 的 class 名带 hash（Qt683QWindowToolSaveBits），
              每个进程/类一般只有一个实例，安全
            * 用 GetClassLongPtr/SetClassLongPtr，64 位要用 Ptr 版
        """
        try:
            import ctypes
            from ctypes import wintypes
            hwnd = int(self.winId())
            user32 = ctypes.windll.user32
            user32.GetClassLongPtrW.restype = ctypes.c_long
            user32.SetClassLongPtrW.restype = ctypes.c_long
            cur = user32.GetClassLongPtrW(hwnd, GCL_STYLE)
            if not (cur & CS_DBLCLKS):
                user32.SetClassLongPtrW(hwnd, GCL_STYLE, cur | CS_DBLCLKS)
        except Exception:
            # 补不上也不能让桌宠起不来 —— 只是双击不可用
            pass

    # -- 绘制 --

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)
        pm = self.sprites.frame(self._current, self._frame_index)

        if self._flip:
            pm = pm.transformed(QTransform().scale(-1, 1))

        w = self.width()
        h = self.height()

        # 忙碌光晕
        if self._glow > 0.01:
            g = QRadialGradient(QPointF(w / 2.0, h * 0.62), w * 0.55)
            c = QColor(242, 122, 26)
            c.setAlpha(int(90 * self._glow))
            g.setColorAt(0.0, c)
            c2 = QColor(255, 176, 92)
            c2.setAlpha(int(40 * self._glow))
            g.setColorAt(1.0, c2)
            p.fillRect(0, 0, w, h, QColor(0, 0, 0, 0))
            p.setBrush(g)
            p.setPen(Qt.NoPen)
            p.drawEllipse(QRectF(w * 0.06, h * 0.12, w * 0.88, h * 0.86))

        # 挤压反馈
        if abs(self._squash) > 0.001:
            sx = 1.0 + self._squash * 0.55
            sy = 1.0 - self._squash
            p.translate(w / 2.0, h)
            p.scale(sx, sy)
            p.translate(-w / 2.0, -h)
            p.drawPixmap(0, 0, w, h, pm)
        else:
            p.drawPixmap(0, 0, w, h, pm)

    # -- 动画 --

    def _interval(self, name):
        meta = self.sprites.meta.get(name) or self.sprites.meta["idle"]
        return max(16, int(1000 / max(1, meta["fps"])))

    def _advance(self):
        frames = self.sprites.frames.get(self._current) or self.sprites.frames["idle"]
        self._frame_index = (self._frame_index + 1) % max(1, len(frames))
        if abs(self._squash) > 0.001:
            self._squash *= 0.72
            if abs(self._squash) < 0.002:
                self._squash = 0.0
        self.update()

    def set_state(self, name, force=False):
        if not force and name == self._current:
            return
        if not self.sprites.has(name):
            name = "idle"
        self._current = name
        self._frame_index = random.randint(0, 3)
        self.anim_timer.start(self._interval(name))
        self._glow = 1.0 if name == "think" else 0.0
        self.update()

    def flip(self):
        self._flip = not self._flip

    def squash(self):
        self._squash = 0.16
        self.update()

    # -- 交互 --

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.press_pos = event.globalPosition().toPoint()
            self.moved = False
            self.setCursor(QCursor(Qt.ClosedHandCursor))
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton and self.press_pos is not None:
            gp = event.globalPosition().toPoint()
            # 坑：drag_to() 必须放在阈值判断**里面**。
            # 之前无条件调用，结果是「按住鼠标时哪怕 1 像素抖动」也会把
            # 桌宠拽到光标处 —— 而点击之前 SetCursorPos 产生的 WM_MOUSEMOVE
            # 可能在按下之后才送达，于是「连点 30 次解锁」的过程中桌宠
            # 会一路乱跑，后面的点击全打空。
            if self.moved or (gp - self.press_pos).manhattanLength() > 6:
                self.moved = True
                self.controller.drag_to(gp)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_offset = None
            self.setCursor(QCursor(Qt.OpenHandCursor))
            if self.moved:
                # 拖拽结束 —— 不计入点击
                self.controller.on_drop()
            elif self._suppress_release:
                # dblclick 后面那个 release —— 第 2 次点击已经在
                # mouseDoubleClickEvent 里计过了，这里不重复计
                self._suppress_release = False
            else:
                self._register_click()
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        """双击事件 —— 它**本身就是一次点击**。

        关键（本轮实机实测踩到，很重要）：
            Windows 把双击的「第 2 次按下」替换成 WM_LBUTTONDBLCLK。
            Qt 收到 dblclick 后**仍会**派发第 2 次点击的 release，
            但如果只数 release，dblclick 分支之外还要再数一次 ->
            双击会被数成 3 次（实测 clicks +3）。
            如果 dblclick 分支里不数，又会漏掉（实测 clicks 只 +1）。

        正确做法：dblclick 里计 1 次，
            再抑制紧随其后的那个 release（它才是重复的那次）。

        另一面：Windows 的 DBLCLK 由鼠标输入队列合成，
            注入事件 / 某些环境下根本不发生 —— 所以两边都要照顾：
              * dblclick 到达   -> 这里计 1 次，抑制后面的 release
              * dblclick 没到达 -> 正常 release 计 1 次（不抑制）
        两种环境下总数一致，判定才稳。
        """
        self._register_click()
        self._suppress_release = True
        event.accept()

        # -- 手势仲裁 --
    #
    # 新规则（2026-11-09，用户定）：
    #     单击 = 额度气泡（贴纸亮着时 = 切回额度气泡「查看」）
    #     双击 = 表情包贴纸
    #     三击 = 只换表情，不再弹贴纸
    #
    # 为什么要「延迟结算」而不是「立刻响应」：
    #     单击和双击在事件层面无法立刻区分 —— 单击的 release 先到，
    #     之后才可能来 dblclick。所以单击必须先挂起，等一小会儿：
    #     等到窗口结束还没等到 dblclick，才认定是单击。
    #     代价是单击响应有 ~220ms 延迟，气泡弹出动画本身 220ms，
    #     肉眼基本无感。
    #
    # 双击后还要再等一小会儿，因为第三次点击可能马上就来：
    #     晚一点判成双击（贴纸已经弹了）比晚一点判成三击好得多 ——
    #     三击会换掉表情，用户会觉得「我只是点了一下怎么脸变了」。

    # 时间参数用模块级常量（见文件顶部 GESTURE_WAIT_MS 等）
    GESTURE_WAIT_MS = globals()["GESTURE_WAIT_MS"]
    TRIPLE_WAIT_MS = globals()["TRIPLE_WAIT_MS"]
    GESTURE_WINDOW_MS = globals()["GESTURE_WINDOW_MS"]

    def _register_click(self):
        """记一次**物理点击**（一次 release），并安排手势结算。

        坑 1（本轮实机发现）：**不能靠 dblclick 事件判双击**。
            Windows 的 WM_LBUTTONDBLCLK 由鼠标输入队列合成，
            注入事件 / 某些环境下根本不发生。
            所以只数 release：1 = 单击，2 = 双击，3 = 三击。
            这在两种环境下结果一致。

        坑 2：彩蛋解锁要连点几十次，如果把「点击计数」和「手势判定」
            混在一起，连点会被判成多击、计数只按手势结算一次
            （实测 count 涨得比实际点击数慢，解锁遥遥无期）。
            所以拆成两层：
              * 计数（egg.tap）在这里做 —— 一次物理点击 = 一次计数
              * 语义（单击/双击/三击）在 _resolve_gesture 里做
        """
        now = time.time()
        if now - self._last_click_at > self.GESTURE_WINDOW_MS / 1000.0:
            # 隔了很久 —— 之前那一串已经结算过了，从头数
            self._clicks = 0
        self._last_click_at = now
        self._clicks += 1
        # 彩蛋解锁计数：每个物理点击都算
        self.controller.on_tap()

        if self._clicks >= 3:
            # 三击：立刻结算，不再等
            self._gesture_timer.stop()
            self._resolve_gesture()
            return
        # 单击 / 双击：等一会儿，看还有没有点击跟上来
        self._gesture_timer.start(self.GESTURE_WAIT_MS)

    def _resolve_gesture(self):
        """手势结算：1 次 = 单击，2 次 = 双击，>=3 次 = 三击。

        判定依据是 **release 次数**（= 真实物理点击数）。
        """
        n = self._clicks
        self._clicks = 0
        if n <= 0:
            return
        if n == 1:
            self.controller.on_single_click()
        elif n == 2:
            self.controller.on_double_click()
        else:
            self.controller.on_triple_click()

    def _on_gesture_timeout(self):
        """手势窗口到期 -> 结算。"""
        self._gesture_timer.stop()
        self._resolve_gesture()

    def contextMenuEvent(self, event):
        self.controller.show_menu(event.globalPos())
        super().contextMenuEvent(event)


# ---------------------------------------------------------------- 控制

class Controller(object):
    # 三击临时切表情后，Hold 这么多秒自动回到「跟随 MiMo」。
    # 不用太长（用户还想继续看那个表情），也不能太短
    # （气泡/动画还没播完就跳回去了会很突兀）。
    T_EXPR_HOLD = 4.0

    def __init__(self, app, cfg_path, cfg):
        self.app = app
        self.cfg_path = cfg_path
        self.cfg = cfg
        self.sprites = None
        self.window = None
        self.bubble = None
        self.tray = None
        self.brain = PetBrain()
        self.listener = None

        self.host_hwnd = None
        self.cx = 0
        self.cy = 0
        self.pet_size = int(cfg.get("size", 220))
        self._owner_set = False
        self._last_owner_hwnd = 0
        self._bubble_owner = 0
        self._wander_at = time.time() + random.uniform(45, 110)
        self._wander_target = None
        self._quota = None
        self._quota_at = 0.0
        self._quota_busy = False
        self._quota_dirty = False
        self._bubble_timer = None
        # 彩蛋：点桌宠攒次数，攒够解锁表情包贴纸
        self.egg = EggTracker()
        # 气泡模式：'quota'（额度信息）| 'sticker'（彩蛋贴纸）
        # 两者共用同一个 BubbleWindow，靠这个字段互斥，防止贴纸
        # 被 _render_bubble 覆盖回额度气泡。
        self._bubble_mode = "quota"
        # 三击临时表情：到期自动回到跟随 MiMo
        self._expr_timer = None
        self._expr_hold_left = 0.0
        # 双击排着待弹的贴纸：等三击窗口过去再弹
        self._sticker_pending = False
        self._sticker_due = 0.0

    # -- 启动 --

    def load(self):
        self.sprites = SpriteSheet(self.cfg["sprite_dir"])
        self.window = PetWindow(self.sprites, self)
        self.window.set_state("idle", force=True)
        self.bubble = BubbleWindow()
        self.bubble.hide()

        self._host_lost_at = None
        self.window.show()
        self.app.processEvents()
        self.attach_host()
        if not self.host_hwnd and self.cfg.get("launch_mimo", True):
            # MiMo 没跑就把它带起来（带调试端口，额度才能读到）
            self.launch_mimo(with_debug=True)

        # 位置：优先用记忆的角落，其次用配置坐标，默认右下角
        cw, ch = self.client_size()
        self._pos_deferred = False
        if not cw or not ch:
            # 桌宠比 MiMo 先起来（watchdog / 计划任务都可能这样）——
            # 此时还没有宿主，客户区尺寸是 0，算出来的坐标是垃圾。
            # 标记成「待定」，等 attach_host() 挂上宿主后再按记忆的角落贴位，
            # 否则桌宠会被永久钉在 MiMo 的左上角。
            self._pos_deferred = True
            self.cx, self.cy = 0, 0
        else:
            self._apply_saved_position(cw, ch)

        self._build_tray()
        self._start_link()

        self.tick_timer = QTimer(self.app)
        self.tick_timer.timeout.connect(self._tick)
        self.tick_timer.start(33)

        self.status_path = os.path.join(HERE, "pet_status.json")
        self.cmd_path = os.path.join(HERE, "pet_cmd.json")
        self._last_cmd_ts = self._existing_cmd_ts()
        self.status_timer = QTimer(self.app)
        self.status_timer.timeout.connect(self._write_status)
        self.status_timer.start(1000)
        self._write_status()

    # ---- MiMo 宿主 ----

    def client_size(self):
        if not self.host_hwnd:
            return (0, 0)
        return H.client_size(self.host_hwnd)

    def _apply_saved_position(self, cw, ch):
        """按配置里记住的角落 / 坐标贴位（客户区坐标）。"""
        x, y = self.cfg.get("x"), self.cfg.get("y")
        corner = self.cfg.get("corner")
        if corner:
            x, y = self.corner_pos(corner, cw, ch)
        if x is None or y is None:
            x, y = (cw - self.pet_size - 24, ch - self.pet_size - 16)
        self.cx = max(0, min(int(x), cw - self.pet_size))
        self.cy = max(0, min(int(y), ch - self.pet_size))

    def attach_host(self):
        """找到 MiMo 主窗口并绑定 owner 关系。"""
        hwnd = self.host_hwnd
        if hwnd and H.user32.IsWindow(hwnd) and H._cls(hwnd) == "Chrome_WidgetWin_1":
            return True
        hwnd = H.find_mimo_window(timeout=0, include_hidden=True)
        if not hwnd:
            self.host_hwnd = None
            return False
        self.host_hwnd = hwnd
        self._owner_set = False
        cw, ch = self.client_size()
        if cw and ch:
            if getattr(self, "_pos_deferred", False):
                # 桌宠先于 MiMo 起来：现在按记忆的角落重新贴位
                self._apply_saved_position(cw, ch)
                self._pos_deferred = False
            else:
                self.cx = max(0, min(self.cx, cw - self.pet_size))
                self.cy = max(0, min(self.cy, ch - self.pet_size))
        return True

    def _apply_owner(self):
        """把桌宠窗口 + 气泡都设成 MiMo 窗口的 owned window。

        坑：Qt 的 show() 会清掉 GWLP_HWNDPARENT（实测），所以必须在窗口
        已经可见之后才设置 owner；这里改成「读实际指针 -> 缺了就补」，
        幂等且不怕 show/hide 来回切。
        """
        if not self.host_hwnd or not self.window:
            return
        if self.window.isVisible():
            hwnd = int(self.window.winId())
            cur = H.user32.GetWindowLongPtrW(hwnd, H.GWLP_HWNDPARENT) or 0
            if cur != self.host_hwnd:
                H.user32.SetWindowLongPtrW(hwnd, H.GWLP_HWNDPARENT,
                                           self.host_hwnd)
                self._owner_set = True
                self._last_owner_hwnd = self.host_hwnd
        if self.bubble and self.bubble.isVisible():
            bh = int(self.bubble.winId())
            cur = H.user32.GetWindowLongPtrW(bh, H.GWLP_HWNDPARENT) or 0
            if cur != self.host_hwnd:
                H.user32.SetWindowLongPtrW(bh, H.GWLP_HWNDPARENT,
                                           self.host_hwnd)
                self._bubble_owner = self.host_hwnd

    def _sync_position(self):
        """按 MiMo 客户区坐标把桌宠摆到正确位置（屏幕坐标）。"""
        if not self.host_hwnd:
            self.window.hide()
            return
        # 宿主最小化 / 收进托盘时，ClientToScreen 会返回 (-32000,-32000) 附近的
        # 哨兵坐标 —— 不挡住的话桌宠会被一起挪到屏幕外。先藏起来。
        if H.user32.IsIconic(self.host_hwnd) or \
                not H.user32.IsWindowVisible(self.host_hwnd):
            self.window.hide()
            return
        ox, oy = H.client_to_screen(self.host_hwnd, 0, 0)
        if ox < -20000 or oy < -20000:
            self.window.hide()
            return
        cw, ch = self.client_size()
        if cw <= 0 or ch <= 0:
            self.window.hide()
            return
        # 夹在客户区内
        self.cx = max(0, min(self.cx, cw - self.pet_size))
        self.cy = max(0, min(self.cy, ch - self.pet_size))
        sx, sy = ox + self.cx, oy + self.cy
        hwnd = int(self.window.winId())
        cur = H._rect(hwnd)
        if (cur[0], cur[1], cur[2] - cur[0], cur[3] - cur[1]) != \
                (sx, sy, self.pet_size, self.pet_size):
            H.user32.SetWindowPos(hwnd, 0, sx, sy, self.pet_size, self.pet_size,
                                  H.SWP_NOZORDER | H.SWP_NOACTIVATE |
                                  H.SWP_NOOWNERZORDER)
        if not self.window.isVisible():
            self.window.show()

    # ---- 贴边 ----

    def corner_pos(self, corner, cw, ch):
        """角落 / 边的贴位坐标（客户区坐标）。

        坑：snap_position() 现在会产出 l/r/t/b 四种「边」标签并存进
        cfg["corner"]。这里如果只认四个角，table.get(corner, table["br"])
        会把边标签静默吞成「右下角」—— 用户把桌宠拖到右边贴住，
        重启后桌宠却自己跳到右下角去了。
        """
        w, h = self.pet_size, self.pet_size
        m = 16
        table = {
            "tl": (m, m), "tr": (cw - w - m, m),
            "bl": (m, ch - h - m), "br": (cw - w - m, ch - h - m),
        }
        if corner in table:
            return table[corner]
        if corner in ("l", "r", "t", "b"):
            # 边：另一轴沿用配置里记住的坐标
            sx = self.cfg.get("x")
            sy = self.cfg.get("y")
            if corner == "l":
                px, py = 0, sy
            elif corner == "r":
                px, py = cw - w, sy
            elif corner == "t":
                px, py = sx, 0
            else:
                px, py = sx, ch - h
            if px is None:
                px = 0
            if py is None:
                py = 0
            return (int(px), int(py))
        return table["br"]

    def snap_position(self, cx, cy, threshold=34):
        """吸附到最近的边/角。返回 (x, y, corner)。"""
        cw, ch = self.client_size()
        if cw <= 0 or ch <= 0:
            return cx, cy, None
        w, h = self.pet_size, self.pet_size
        cands = []
        # 四角
        for tag, (px, py) in (("tl", (0, 0)), ("tr", (cw - w, 0)),
                              ("bl", (0, ch - h)), ("br", (cw - w, ch - h))):
            d = math.hypot(px - cx, py - cy)
            if d <= threshold * 1.6:
                cands.append((d, px, py, tag))
        # 四边（保持当前另一轴坐标）
        for tag, (px, py) in (("l", (0, cy)), ("r", (cw - w, cy)),
                              ("t", (cx, 0)), ("b", (cx, ch - h))):
            d = abs(px - cx) + abs(py - cy)
            if d <= threshold:
                cands.append((d * 0.9, px, py, tag))
        if not cands:
            # 没到阈值就夹到最近边但不吸附
            return (max(0, min(cx, cw - w)), max(0, min(cy, ch - h)), None)
        cands.sort(key=lambda c: c[0])
        _, px, py, tag = cands[0]
        return int(px), int(py), tag

    def on_drop(self):
        if not self.cfg.get("snap", True):
            self._save_pos()
            return
        x, y, corner = self.snap_position(self.cx, self.cy)
        self.cx, self.cy = x, y
        if corner:
            self.cfg["corner"] = corner
        self._save_pos()

    def _save_pos(self):
        # 位置还没定下来（桌宠先于 MiMo 起来）时**不要落盘**——
        # 否则退化的 (0,0) 会在退出时被写回配置，把用户记住的坐标冲掉，
        # 下次启动桌宠就贴到左上角去了。
        if getattr(self, "_pos_deferred", False):
            return
        self.cfg["x"] = int(self.cx)
        self.cfg["y"] = int(self.cy)
        self.save_config()

    # ---- 溜达 ----

    def _tick_wander(self):
        if not self.cfg.get("wander", True):
            return
        if self._wander_target is not None:
            tx, ty, corner = self._wander_target
            step = 6
            dx, dy = tx - self.cx, ty - self.cy
            dist = math.hypot(dx, dy)
            if dist <= step:
                self.cx, self.cy = tx, ty
                self._wander_target = None
                if corner:
                    self.cfg["corner"] = corner
                self._save_pos()
            else:
                self.cx += int(dx / dist * step)
                self.cy += int(dy / dist * step)
            return
        if time.time() < self._wander_at:
            return
        cw, ch = self.client_size()
        if cw <= 0:
            return
        self._wander_at = time.time() + random.uniform(50, 120)
        corner = random.choice(["tl", "tr", "bl", "br"])
        tx, ty = self.corner_pos(corner, cw, ch)
        self._wander_target = (int(tx), int(ty), corner)

    # ---- 拖拽 ----

    def drag_to(self, global_pos):
        if not self.host_hwnd:
            return
        cx, cy = H.screen_to_client(self.host_hwnd, global_pos.x(), global_pos.y())
        cw, ch = self.client_size()
        w, h = self.pet_size, self.pet_size
        self.cx = max(-w // 3, min(cx - w // 2, cw - w + w // 3))
        self.cy = max(-h // 3, min(cy - h // 2, ch - h + h // 3))
        self._wander_target = None

    # ---- 点击 ----

    def on_tap(self):
        """记一次物理点击（彩蛋解锁计数）。

        单独拆出来是因为：彩蛋解锁要连点几十次，而连点会被
        手势仲裁判成多击。如果计数跟着手势走，解锁就永远差一点。
        """
        self.egg.tap()

    def on_single_click(self):
        """单击 = 弹额度气泡（状态 + 小米额度）。

        贴纸（彩蛋）亮着时单击 = **切回额度气泡**（用户 2026-11-09 定：
        「有表情包单击是查看」—— 回到额度那张卡去看用量）。
        单击永远不换贴纸、也不出贴纸。

        彩蛋解锁门槛靠点击次数累计（在 _register_click 里按物理点击计）。
        """
        self.window.squash()
        # 贴纸亮着 -> 切回额度气泡
        if self._bubble_mode == "sticker":
            self.show_bubble()
            return
        # 额度气泡已开 -> 收起（再点一下关掉）
        if self.bubble.isVisible():
            self.hide_bubble()
            return
        self.show_bubble()

    def on_double_click(self):
        """双击 = 弹表情包贴纸（彩蛋）。

        贴纸开着时再双击 = 换下一张。
        单击不参与贴纸的切换（见 on_single_click）。

        未解锁时只提示还差几次，不弹贴纸 ——
        这样「多点几十次」这个彩蛋门槛才有意义。

        注意：这里**先不弹**，而是排一个延迟。
        原因是三击：新规则里三击 = 只换表情、不出贴纸。
        如果双击就立刻弹贴纸，三击时贴纸已经亮着了，
        三击再弹一次会闪一下 —— 用户看到的就是「三击也出贴纸」。
        所以等三击窗口过去、确定没有第三次点击，再弹。
        """
        self.window.squash()
        if not self.egg.unlocked:
            remaining = max(0, self.egg.unlock_at - self.egg.clicks)
            self._toast("再多点几下试试？还差 %d 次" % remaining)
            return
        # 关键：立刻占位成 sticker 模式。
        # 贴纸要等 TRIPLE_WAIT_MS 才弹，这段时间里 _bubble_mode
        # 如果还是 "quota"，_refresh_bubble_content 会在额度数据
        # 回来时把气泡重绘成额度卡片 —— 贴纸就永远弹不出来。
        self._bubble_mode = "sticker"
        self._sticker_pending = True
        self._sticker_due = time.time() + TRIPLE_WAIT_MS / 1000.0

    def _show_next_sticker(self):
        """延迟到期 —— 确实不是三击，弹贴纸。

        坑（本轮实测踩到）：这里**不要用 QTimer**。
            QTimer(self.app) 和 QTimer.singleShot 在这个项目里
            都不触发（active=True 但 timeout 不来）——
            真实鼠标事件的回调链路和主事件循环的定时器不兼容。
            改成在 _tick 里轮询时间戳，一定在主线程，稳定。
        """
        self._sticker_pending = False
        item = self.egg.next_sticker()
        if item is None:
            self.show_bubble()
            return
        self.show_sticker(item)

    def on_triple_click(self):
        """三击 = 只换表情，**不再弹贴纸**（用户 2026-11-09 定）。

        原来的规则是「双击/三击都出贴纸」，三击只切个表情。
        现在彩蛋归双击，三击专门用来换表情：
        切完 T_EXPR_HOLD 秒自动回到「跟随 MiMo」，
        不做手动锁定，免得用户忘了自己锁过表情。

        还要取消双击排着的那张贴纸 —— 三击不该出贴纸。
        """
        self.window.squash()
        self._sticker_pending = False
        # 贴纸没弹出来，模式归位（别让气泡卡在 sticker 模式）
        self._bubble_mode = "quota"
        self.cycle_expression(temporary=True)

    def cycle_expression(self, temporary=False):
        """轮换表情（idle -> happy -> think -> tired）。

        temporary=True = 临时切一下，切完 T_EXPR_HOLD 秒
        自动回到「跟随 MiMo」（三击走这条路）。
        temporary=False = 手动锁定，右键菜单里那四个选项走这条路。
        """
        order = ["idle", "happy", "think", "tired"]
        cur = self.brain.manual or self.brain.state
        nxt = order[(order.index(cur) + 1) % len(order)] if cur in order else "idle"
        if temporary:
            self._set_temporary(nxt)
        else:
            self._set_manual(nxt)

    def _set_temporary(self, state):
        """临时表情：显示 state，hold 秒后自动回到跟随 MiMo。

        坑：不能靠 brain.manual 手动锁 —— 手动锁只有用户自己
        在右键菜单里解除，忘了就永远卡在那个表情上。
        所以这里用一个独立的计时器，到点直接清掉。
        """
        self.brain.set_manual(state)
        self.window.set_state(state)
        self._expr_hold_left = self.T_EXPR_HOLD
        if self._expr_timer is None:
            self._expr_timer = QTimer(self.app)
            self._expr_timer.setSingleShot(True)
            self._expr_timer.timeout.connect(self._release_temporary)
        self._expr_timer.stop()
        self._expr_timer.start(int(self.T_EXPR_HOLD * 1000))

    def _release_temporary(self):
        """临时表情到期 -> 解除手动锁，回到跟随 MiMo。"""
        self.brain.release_manual()
        self.window.set_state(self.brain.state)

    # ---- MiMo 启动 / 调试端口 ----

    def cdp_available(self):
        """MiMo 是否带调试端口在跑（额度读取的前提）。"""
        try:
            from mimo_cdp import MiMoCDP
            return MiMoCDP(port=CDP_PORT).available()
        except Exception:
            return False

    def launch_mimo(self, with_debug=True):
        """启动 MiMo（默认带调试端口）。"""
        import subprocess
        if not os.path.isfile(MIMO_EXE):
            self._toast("找不到 MiMo 程序：%s" % MIMO_EXE)
            return False
        args = [MIMO_EXE, "--updated"]
        if with_debug:
            args.append("--remote-debugging-port=%d" % CDP_PORT)
        try:
            subprocess.Popen(args, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
            self._toast("正在启动 MiMo…")
            # 自己拉起来的 MiMo，窗口可能是隐藏的（进程在、窗口不在）。
            # 桌宠是 owned window，owner 隐藏它也跟着隐藏 -> 两头都看不见。
            # 这里主动把窗口叫出来。
            def _show():
                try:
                    H.show_mimo_window(timeout=15.0)
                except Exception:
                    pass
            threading.Thread(target=_show, daemon=True).start()
            return True
        except Exception as e:
            self._toast("启动 MiMo 失败：%s" % e)
            return False

    def relaunch_mimo_debug(self):
        """重启 MiMo 并带上调试端口（这样才能读到额度）。"""
        import ctypes
        from ctypes import wintypes as wt
        H.user32.PostMessageW.argtypes = [wt.HWND, ctypes.c_uint,
                                          ctypes.c_ulonglong,
                                          ctypes.c_longlong]
        H.user32.PostMessageW.restype = wt.BOOL
        host = self.host_hwnd or H.find_mimo_window(timeout=2,
                                                     include_hidden=True)
        if host:
            H.user32.PostMessageW(host, 0x0010, 0, 0)     # WM_CLOSE
            for _ in range(24):
                time.sleep(0.5)
                if not H.find_mimo_window(timeout=0, include_hidden=True):
                    break
        self.host_hwnd = None
        self.window.hide()
        self.launch_mimo(with_debug=True)

    # ---- 气泡 ----

    def show_bubble(self):
        """弹出额度气泡。默认 bubble_timeout 秒后自动收起。

        用户要求「自动收起可以保留，但时间要长」，
        同时「再点一次桌宠也能收起」。

        这个方法同时负责「从贴纸模式切回额度模式」——
        贴纸亮着时单击桌宠就是走这里（用户 2026-11-09 定：
        「有表情包单击是查看」）。set_content() 开头会清掉 _sticker，
        所以贴纸会真的被换掉，不会两个模式叠在一起。
        """
        self._render_bubble()       # 先用现有数据渲染，保证气泡秒弹
        self.bubble.pop_in()
        self._apply_owner()         # show() 会清 owner，弹出的瞬间就补上
        self._arm_bubble_timer()
        self._refresh_quota(force=True)   # 额度放到后台拉，回来再刷新内容
        self._bubble_mode = "quota"

    def hide_bubble(self):
        self.bubble.fade_out()
        self._bubble_mode = "quota"
        if self._bubble_timer:
            self._bubble_timer.stop()
        # 有贴纸排着没弹？一起取消，免得它过一会儿又冒出来
        self._sticker_pending = False

    # ---- 彩蛋贴纸 ----

    def show_sticker(self, item, fresh=False):
        """弹一张表情包贴纸（彩蛋）。

        贴纸本身自带超大标题（「罢工」「困了」「划水摸鱼」），
        所以气泡里不再重复标题，只放状态行 + 收起提示 ——
        避免同一个词出现两次。

        桌宠同时切到贴纸对应的表情（think/tired/idle/happy），
        让「气泡内容」和「桌宠表情」讲同一个故事。

        坑：切表情会让 MiMo 的 SSE 事件把状态打回 happy，
        而 _apply_state 在 happy 时会 show_bubble() —— 那会把贴纸
        覆盖回额度气泡。所以这里用 _bubble_mode 显式互斥：
        贴纸模式下 _apply_state 不许抢气泡。
        """
        if not item:
            return
        pm = self.egg.pack.pixmap(item)
        if pm.isNull():
            return

        mood = item.get("mood") or "idle"
        if self.sprites.has(mood):
            self.window.set_state(mood)

        sub = "%s %s" % (STATE_EMOJI.get(mood, "✦"),
                         STATE_LABEL.get(mood, mood))
        footer = self._sticker_footer()
        self.bubble.set_sticker(pm, title="", sub=sub, footer=footer,
                                dark=bool(item.get("dark")))
        self.bubble.pop_in()
        self._apply_owner()
        self._arm_bubble_timer()
        self._bubble_mode = "sticker"


        if fresh:
            self._toast("彩蛋解锁！再点桌宠可以抽新表情包")

    def _bubble_footer(self):
        tip = "再点桌宠收起"
        t = int(self.cfg.get("bubble_timeout", 60) or 0)
        if t > 0:
            tip += " · %d 秒后自动收起" % t
        return tip

    def _sticker_footer(self):
        """贴纸气泡的脚注 —— 提示怎么切回额度气泡。"""
        tip = "单击切回额度"
        t = int(self.cfg.get("bubble_timeout", 60) or 0)
        if t > 0:
            tip += " · %d 秒后自动收起" % t
        return tip

    def _bubble_is_sticker(self):
        """当前气泡是不是贴纸（彩蛋）模式。"""
        return getattr(self.bubble, "_sticker", None) is not None

    def show_random_sticker(self):
        """手动抽一张贴纸。"""
        if not len(self.egg.pack):
            self._toast("没有找到表情包素材")
            return
        item = self.egg.pack.by_index(random.randint(0, len(self.egg.pack) - 1))
        self.show_sticker(item)

    def unlock_eggs(self):
        """直接解锁彩蛋（跳过点击次数）。"""
        self.egg.clicks = max(self.egg.clicks, self.egg.unlock_at)
        self.egg.unlocked = True
        self.egg._save()
        self._toast("彩蛋已解锁")
        self.show_random_sticker()

    def reset_eggs(self):
        self.egg.reset()
        self._toast("彩蛋进度已重置")

    def _arm_bubble_timer(self):
        """复用同一个定时器（每次 new QTimer 会泄漏），按配置决定是否自动收起。"""
        timeout = int(self.cfg.get("bubble_timeout", 5) or 0)
        if self._bubble_timer is None:
            self._bubble_timer = QTimer(self.app)
            self._bubble_timer.setSingleShot(True)
            self._bubble_timer.timeout.connect(lambda: self.bubble.fade_out())
        self._bubble_timer.stop()
        if timeout > 0:
            self._bubble_timer.start(timeout * 1000)

    def _render_bubble(self):
        st = self.brain.manual or self.brain.state
        rows = []
        bar = None
        q = self._quota
        if q is None:
            rows.append(("额度", "读取中…"))
        else:
            if q.get("error"):
                rows.append(("额度", _quota_error_text(q["error"])))
            pct = q.get("percent")
            if pct is not None:
                rows.append(("额度剩余", "%d%%" % round(pct)))
                bar = (pct / 100.0 if pct <= 1.0 else pct,
                       C_ORANGE if (pct if pct > 1 else pct * 100) > 20
                       else QColor(206, 66, 52))
            used_pct = q.get("percent_used")
            if used_pct is not None:
                rows.append(("本月已用", "%d%%" % round(used_pct * 100)))
            bal = q.get("balance")
            if bal is not None:
                cur = q.get("currency") or "CNY"
                sym = "¥" if cur.upper() in ("CNY", "RMB") else ""
                rows.append(("账户余额", "%s%s" % (sym, bal)))
            if q.get("plan"):
                label = q["plan"]
                status = PLAN_STATUS.get(str(q.get("plan_status") or "").upper())
                if status:
                    label = "%s（%s）" % (label, status)
                rows.append(("套餐", label))
            if q.get("plan_end"):
                rows.append(("套餐到期", _short_date(q["plan_end"])))
            reset = q.get("reset_date") or q.get("plan_reset")
            if reset:
                rows.append(("额度重置", _short_date(reset)))
            used = q.get("used")
            if used:
                rows.append(("本轮消耗", _fmt_num(used) + " tok"))
        rows.append(("MiMo 连接", "已连接" if (self.listener and self.listener.connected)
                     else "未连接"))
        tip = self._bubble_footer()
        # 快解锁时给一点暗示（别太早暴露彩蛋）
        hint = self.egg.hint() if hasattr(self, "egg") else ""
        if hint:
            tip = hint + " · " + tip
        else:
            # 已解锁之后，明确告诉用户「双击抽表情包」
            if getattr(self, "egg", None) and self.egg.unlocked:
                tip = "双击桌宠抽表情包 · " + tip
        self.bubble.set_content(
            "%s %s" % (STATE_EMOJI.get(st, "✦"), STATE_LABEL.get(st, st)),
            rows,
            subtitle="MiMo 桌面伙伴",
            bar=bar,
            footer=tip,
            tail_side="bottom", tail_x=0.5)

    def _refresh_quota(self, force=False):
        """后台刷新额度（不阻塞 UI 线程）。

        额度要走 CDP 问 MiMo 自己，一来一回要 1~3 秒。
        旧版是在 UI 线程里同步拉，结果是「点了桌宠没反应，过几秒气泡才冒出来」。
        现在改成后台线程拉，气泡立刻弹出，数据回来再填进去。
        """
        if getattr(self, "_quota_busy", False):
            return
        now = time.time()
        if not force and now - self._quota_at < 30:
            return
        self._quota_at = now
        self._quota_busy = True
        t = threading.Thread(target=self._quota_worker, daemon=True)
        t.start()

    def _quota_worker(self):
        try:
            from mimo_quota import QuotaClient
            if not hasattr(self, "_qc"):
                self._qc = QuotaClient()
            self._quota = self._qc.get(force=True)
        except Exception as e:
            self._quota = {"error": str(e)}
        finally:
            self._quota_busy = False
            self._quota_dirty = True

    # ---- 外部控制通道 ----

    def _existing_cmd_ts(self):
        try:
            with open(self.cmd_path, "r", encoding="utf-8") as f:
                return int(json.load(f).get("ts") or 0)
        except Exception:
            return 0

    def _write_status(self):
        try:
            data = {
                "pid": os.getpid(),
                "state": self.brain.state,
                "manual": self.brain.manual,
                "session": self.brain.session_id,
                "last_event": self.brain.last_event,
                "connected": bool(self.listener and self.listener.connected),
                "last_error": (self.listener.last_error if self.listener else None),
                "sprite_dir": self.cfg.get("sprite_dir"),
                "visible": bool(self.window and self.window.isVisible()),
                "hosted": bool(self.host_hwnd),
                "host_rect": H._rect(self.host_hwnd) if self.host_hwnd else None,
                "pos": [self.cx, self.cy],
                "corner": self.cfg.get("corner"),
                "quota": self._quota,
                "egg": {
                    "clicks": self.egg.clicks,
                    "unlocked": self.egg.unlocked,
                    "unlock_at": self.egg.unlock_at,
                    "collected": len(set(self.egg.seen)),
                    "total": len(self.egg.pack),
                    "sticker_mode": self._bubble_is_sticker(),
                },
                "updated": int(time.time() * 1000),
            }
            with open(self.status_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _poll_cmd(self):
        try:
            if not os.path.isfile(self.cmd_path):
                return
            with open(self.cmd_path, "r", encoding="utf-8") as f:
                cmd = json.load(f)
        except Exception:
            return
        ts = cmd.get("ts")
        if not ts or ts == self._last_cmd_ts:
            return
        self._last_cmd_ts = ts
        action = cmd.get("action")
        if action == "set":
            st = cmd.get("state")
            self.brain.set_manual(st)
            self.window.set_state(self.brain.manual or self.brain.state)
        elif action == "auto":
            self.brain.release_manual()
            self.window.set_state(self.brain.state)
        elif action == "reload":
            self._reload()
        elif action == "show":
            self.window.show()
        elif action == "hide":
            self.window.hide()
        elif action == "bubble":
            self.show_bubble()
        elif action == "hidebubble":
            # 主动收起气泡并把模式归位到「额度」——
            # 测试脚本需要确定性的起点（否则上一轮留下的贴纸气泡
            # 会让下一次单击变成「收起贴纸」而不是「弹额度气泡」）
            self.hide_bubble()
        elif action == "egg":
            # 彩蛋：sticker=抽一张 / unlock=直接解锁 / reset=重置
            what = cmd.get("what") or "sticker"
            if what == "unlock":
                self.unlock_eggs()
            elif what == "reset":
                self.reset_eggs()
            else:
                self.show_random_sticker()
        elif action == "corner":
            tag = cmd.get("corner")
            if tag in ("tl", "tr", "bl", "br"):
                self._go_corner(tag)
        elif action == "quit":
            self.quit()

    # ---- 托盘 / 事件 ----

    def _build_tray(self):
        icon_pm = self.sprites.frame("idle", 0).scaled(
            QSize(64, 64), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.tray = QSystemTrayIcon(QIcon(icon_pm), self.app)
        self.tray.setToolTip("MiMo 桌宠")
        self.tray.activated.connect(self._tray_activated)
        self.tray.show()

    def _tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self.show_bubble()
        elif reason == QSystemTrayIcon.Context:
            self.show_menu(self.tray.geometry().bottomLeft())

    def _start_link(self):
        if not self.cfg.get("follow_mimo", True):
            return
        client = MimoClient()
        self.listener = MimoListener(self.brain, client=client,
                                      on_change=self._on_state,
                                      on_event=self._on_event)
        self.listener.start()

    def _on_event(self, ev_type, payload):
        """把 SSE 的 usage 事件里的 token 数记进额度统计。"""
        if str(ev_type).lower() != "ui":
            return
        ui = (payload or {}).get("ui") or {}
        if str(ui.get("kind") or "") != "usage":
            return
        n = _extract_tokens(ui)
        if not n:
            return
        try:
            if not hasattr(self, "_qc"):
                from mimo_quota import QuotaClient
                self._qc = QuotaClient()
            self._qc.note_usage(n)
            if self._quota:
                self._quota["used"] = self._qc.session_tokens()
        except Exception:
            pass

    def _on_state(self, state):
        QTimer.singleShot(0, lambda: self._apply_state(state))

    def _apply_state(self, state):
        if self.brain.manual:
            return
        self.window.set_state(state)
        # 贴纸（彩蛋）模式下不许额度气泡抢位置 —— 否则贴纸一弹出来
        # 就会被 MiMo 的 happy 事件刷回额度气泡。
        if state == "happy" and self.cfg.get("show_balloon", True) \
                and self._bubble_mode != "sticker" \
                and not self._sticker_pending:
            self.show_bubble()

    def _tick(self):
        if not self.attach_host():
            self.window.hide()
            self._maybe_exit_with_mimo()
        else:
            self._host_lost_at = None
            self._sync_position()      # 可能触发 show()
            self._apply_owner()        # show 之后才绑 owner
            self._tick_wander()
            if self.bubble.isVisible():
                self._place_bubble()
                self._refresh_bubble_content()
        if self.brain.tick():
            self._apply_state(self.brain.state)
        self._poll_cmd()
        # 待弹的贴纸：到点了就弹（用轮询而不是 QTimer，见
        # _show_next_sticker 的说明）
        if self._sticker_pending and \
                time.time() >= getattr(self, "_sticker_due", 0):
            self._show_next_sticker()

    def _maybe_exit_with_mimo(self):
        """MiMo 关了 -> 桌宠跟着退出（联动模式）。

        用户要求：「MiMo 开启就联动唤醒，MiMo 关闭就关闭」。
        宽限 exit_grace 秒 —— MiMo 冷启动时窗口会晚几秒才出现。
        退出**不写** pet_disabled：那是「用户主动退出」的语义。
        联动退出后 MiMo 再开，常驻的 launcher --watch 会重新唤醒桌宠。
        """
        if not self.cfg.get("link_mimo", True):
            return
        now = time.time()
        if getattr(self, "_host_lost_at", None) is None:
            self._host_lost_at = now
            return
        try:
            grace = float(self.cfg.get("exit_grace", 8.0))
        except Exception:
            grace = 8.0
        if now - self._host_lost_at < grace:
            return
        self._exit_for_mimo()

    def _exit_for_mimo(self):
        """联动退出（不写「已停用」标记）。"""
        try:
            self._save_pos()
        except Exception:
            pass
        for fn in (lambda: self.listener and self.listener.stop(),
                   lambda: self.tray and self.tray.hide()):
            try:
                fn()
            except Exception:
                pass
        self.app.quit()

    def _refresh_bubble_content(self):
        """气泡挂着时定期把额度刷新进去。

        额度是后台线程拉的，这里只在「后台拉完了」时重绘一次，
        并顺手预约下一轮刷新。

        注意：贴纸气泡（彩蛋）不能被额度重绘覆盖 —— 否则贴纸一弹出来
        就会被下一帧刷成额度气泡。所以贴纸模式下只刷额度、不重绘内容。
        """
        if getattr(self, "_quota_dirty", False):
            self._quota_dirty = False
            if self._bubble_mode != "sticker" and not self._sticker_pending:
                self._render_bubble()
        self._refresh_quota(force=False)

    def _place_bubble(self):
        ox, oy = H.client_to_screen(self.host_hwnd, 0, 0)
        cw, ch = self.client_size()
        px = ox + self.cx
        py = oy + self.cy
        x, y, side, tx = place_bubble(self.bubble, px, py,
                                      self.pet_size, self.pet_size,
                                      ox, oy, cw, ch)
        self.bubble.move(x, y)
        self.bubble.set_tail(side, tx)

    # -- 菜单 --

    def show_menu(self, pos):
        m = QMenu()
        m.setStyleSheet(
            "QMenu{background:#20202a;color:#f0f0f5;border:1px solid #3a3a48;"
            "padding:6px}QMenu::item{padding:6px 22px;border-radius:4px}"
            "QMenu::item:selected{background:#b45309;color:#fff}")

        sub = m.addMenu("表情")
        auto = sub.addAction("跟随 MiMo（自动）")
        auto.setCheckable(True)
        auto.setChecked(self.brain.manual is None)
        auto.triggered.connect(lambda: self._set_manual(None))
        for st in ("idle", "happy", "think", "tired"):
            act = sub.addAction("%s — %s" % (st, STATE_LABEL[st]))
            act.setCheckable(True)
            act.setChecked(self.brain.manual == st)
            act.triggered.connect(lambda _c=False, s=st: self._set_manual(s))
        sub.addSeparator()
        sub.addAction("轮换表情（idle→happy→think→tired）").triggered.connect(
            self.cycle_expression)
        sub.addAction("临时换表情（%d 秒后回到跟随）"
                      % int(self.T_EXPR_HOLD)).triggered.connect(
            lambda: self.cycle_expression(temporary=True))

        csub = m.addMenu("位置")
        for tag, name in (("tl", "左上"), ("tr", "右上"),
                          ("bl", "左下"), ("br", "右下")):
            act = csub.addAction(name)
            act.setCheckable(True)
            act.setChecked(self.cfg.get("corner") == tag)
            act.triggered.connect(lambda _c=False, t=tag: self._go_corner(t))

        m.addSeparator()
        snap = m.addAction("拖拽后自动贴边")
        snap.setCheckable(True)
        snap.setChecked(bool(self.cfg.get("snap", True)))
        snap.triggered.connect(self._toggle_snap)

        wnd = m.addAction("空闲自动溜达")
        wnd.setCheckable(True)
        wnd.setChecked(bool(self.cfg.get("wander", True)))
        wnd.triggered.connect(self._toggle_wander)

        follow = m.addAction("跟随 MiMo 状态")
        follow.setCheckable(True)
        follow.setChecked(bool(self.cfg.get("follow_mimo", True)))
        follow.triggered.connect(self._toggle_follow)

        m.addSeparator()
        m.addAction("查看额度气泡").triggered.connect(self.show_bubble)
        m.addAction("收起气泡").triggered.connect(self.hide_bubble)
        # 彩蛋：手动抽一张 / 直接解锁
        egg_menu = m.addMenu("彩蛋表情包")
        egg_menu.addAction("抽一张").triggered.connect(self.show_random_sticker)
        egg_menu.addAction("立即解锁（%d 次）" % self.egg.unlock_at).triggered.connect(
            self.unlock_eggs)
        egg_menu.addAction("重置彩蛋进度").triggered.connect(self.reset_eggs)
        if not self.host_hwnd:
            m.addAction("启动 MiMo").triggered.connect(
                lambda: self.launch_mimo(with_debug=True))
        elif not self.cdp_available():
            m.addAction("重启 MiMo（启用额度读取）").triggered.connect(
                self.relaunch_mimo_debug)
        m.addAction("显示 / 隐藏").triggered.connect(self._toggle_visible)
        m.addAction("重新加载素材").triggered.connect(self._reload)
        m.addAction("开机自启").triggered.connect(self._toggle_autostart)
        m.addAction("关于").triggered.connect(self._about)
        m.addAction("退出").triggered.connect(self.quit)
        m.exec(pos)

    def _go_corner(self, tag):
        cw, ch = self.client_size()
        if cw <= 0:
            return
        x, y = self.corner_pos(tag, cw, ch)
        self.cx, self.cy = int(x), int(y)
        self.cfg["corner"] = tag
        self._save_pos()
        self._wander_target = None

    def _toggle_snap(self):
        self.cfg["snap"] = not self.cfg.get("snap", True)
        self.save_config()

    def _toggle_wander(self):
        self.cfg["wander"] = not self.cfg.get("wander", True)
        self._wander_target = None
        self.save_config()

    def _toggle_follow(self):
        self.cfg["follow_mimo"] = not self.cfg.get("follow_mimo", True)
        if self.cfg["follow_mimo"] and not self.listener:
            self._start_link()
        elif not self.cfg["follow_mimo"] and self.listener:
            self.listener.stop()
            self.listener = None
        self.save_config()

    def _toggle_visible(self):
        if self.window.isVisible():
            self.window.hide()
        else:
            self.window.show()

    def _set_manual(self, state):
        self.brain.set_manual(state)
        self.window.set_state(self.brain.manual or self.brain.state)
        self.save_config()

    def _reload(self):
        try:
            self.sprites = SpriteSheet(self.cfg["sprite_dir"])
            self.window.sprites = self.sprites
            self.window.set_state(self.window._current, force=True)
            self._toast("素材已重新加载")
        except Exception as e:
            QMessageBox.warning(None, "MiMo 桌宠", "重新加载失败: %s" % e)

    def _about(self):
        m = self.sprites.manifest
        QMessageBox.information(
            None, "关于 MiMo 桌宠",
            "MiMo 桌面伙伴（住在 MiMo 窗口里）\n"
            "sprite: %s (%dx%d)\n"
            "帧尺寸: %dx%d, 列数 %d, 总帧 %d\n"
            "动画: %s\n\n"
            "宿主窗口: %s\n"
            "状态源: MiMo Desktop 本地 API /v1/sessions/<id>/events"
            % (m.get("id"), self.sprites.sheet.width(), self.sprites.sheet.height(),
               m.get("frameWidth"), m.get("frameHeight"), m.get("columns"),
               m.get("totalFrames"), ", ".join(sorted(self.sprites.frames.keys())),
               H.describe(self.host_hwnd) if self.host_hwnd else "未找到"))

    def _toast(self, text):
        if self.tray:
            self.tray.showMessage("MiMo 桌宠", text, QSystemTrayIcon.Information, 2200)

    # ---- 开机自启 ----

    def _startup_cmd(self):
        return os.path.join(os.environ.get("APPDATA", ""),
                            "Microsoft", "Windows", "Start Menu",
                            "Programs", "Startup", "MiMo桌宠.cmd")

    def _autostart_enabled(self):
        return os.path.isfile(self._startup_cmd())

    def _autostart_body(self):
        """开机自启脚本内容（GBK 写盘）。

        cmd.exe 在简体中文系统下按 ANSI(GBK) 读 .cmd，
        用 UTF-8 写会把中文路径弄成乱码 -> 必须写 GBK。
        MiMo 也要用 --remote-debugging-port 启动，否则读不到额度。
        """
        py = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
        exe = py if os.path.isfile(py) else sys.executable
        lines = ["@echo off"]
        if os.path.isfile(MIMO_EXE):
            lines.append('start "" "%s" --updated --remote-debugging-port=%d'
                         % (MIMO_EXE, CDP_PORT))
        lines.append('start "" "%s" "%s"'
                     % (exe, os.path.join(HERE, "mimo_pet.py")))
        return "\r\n".join(lines) + "\r\n"

    def _toggle_autostart(self):
        p = self._startup_cmd()
        try:
            if os.path.isfile(p):
                os.remove(p)
                self._toast("已关闭开机自启")
            else:
                os.makedirs(os.path.dirname(p), exist_ok=True)
                body = self._autostart_body()
                try:
                    with open(p, "w", encoding="gbk", errors="replace") as f:
                        f.write(body)
                except Exception:
                    with open(p, "wb") as f:
                        f.write(body.encode("gbk", errors="replace"))
                self._toast("已设置开机自启")
        except Exception as e:
            self._toast("开机自启设置失败: %s" % e)

    def _write_autostart(self):
        """无条件重写开机自启脚本（修复编码问题用）。"""
        p = self._startup_cmd()
        os.makedirs(os.path.dirname(p), exist_ok=True)
        body = self._autostart_body()
        with open(p, "wb") as f:
            f.write(body.encode("gbk", errors="replace"))
        return p

    # -- 配置持久化 --

    def save_config(self):
        try:
            with open(self.cfg_path, "w", encoding="utf-8") as f:
                json.dump(self.cfg, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def quit(self):
        # 用户主动关掉 -> 写「已停用」标记，watchdog / 计划任务才不会
        # 把它立刻拉回来。
        try:
            with open(DISABLED_FILE, "w", encoding="utf-8") as f:
                f.write("user quit at %s\n" % time.strftime("%Y-%m-%d %H:%M:%S"))
        except Exception:
            pass
        self._save_pos()
        if self.listener:
            self.listener.stop()
        if self.tray:
            self.tray.hide()
        self.app.quit()


# ---------------------------------------------------------------- 入口

def load_config(path):
    cfg = dict(DEFAULT_CFG)
    saved = {}
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                saved = json.load(f)
            cfg.update(saved)
        except Exception:
            saved = {}
    # 布局语义变了（v1 是桌面浮窗的屏幕坐标，v2 是 MiMo 客户区坐标）-> 位置重置
    if saved.get("layout_version") != DEFAULT_CFG["layout_version"]:
        cfg["x"] = None
        cfg["y"] = None
        cfg["corner"] = DEFAULT_CFG["corner"]
        cfg["layout_version"] = DEFAULT_CFG["layout_version"]
    return cfg


def main():
    cfg_path = DEFAULT_CONFIG
    args = sys.argv[1:]
    if "--config" in args:
        cfg_path = args[args.index("--config") + 1]
    cfg = load_config(cfg_path)

    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    if "--selftest" in args:
        return selftest(app, cfg)

    ctl = Controller(app, cfg_path, cfg)
    try:
        ctl.load()
    except Exception as e:
        QMessageBox.critical(None, "MiMo 桌宠",
                              "启动失败：%s\n\n素材目录: %s" % (e, cfg["sprite_dir"]))
        return 2

    if not cfg.get("start_minimized"):
        ctl.window.show()
    app.exec()
    return 0


def selftest(app, cfg):
    """不进入事件循环：渲染每个表情各一帧 + 气泡，存 PNG。"""
    outdir = os.path.join(HERE, "selftest")
    os.makedirs(outdir, exist_ok=True)
    try:
        sp = SpriteSheet(cfg["sprite_dir"])
    except Exception as e:
        print("SELFTEST FAIL: 素材加载失败: %s" % e)
        return 2
    print("SELFTEST 精灵图 %dx%d, 帧 %dx%d, 动画 %s"
          % (sp.sheet.width(), sp.sheet.height(), sp.fw, sp.fh,
             sorted(sp.frames.keys())))
    ctl = Controller.__new__(Controller)
    ctl.cfg = cfg
    ctl.sprites = sp
    ctl.brain = PetBrain()
    ctl.tray = None
    ctl.listener = None
    ctl.pet_size = int(cfg.get("size", 220))
    w = PetWindow(sp, ctl)
    w.resize(ctl.pet_size, ctl.pet_size)
    for name in sorted(sp.frames.keys()):
        w.set_state(name, force=True)
        w._frame_index = 0
        pm = w.grab()
        p = os.path.join(outdir, "state-%s.png" % name)
        pm.save(p)
        print("  渲染 %-6s -> %s (%dx%d)" % (name, p, pm.width(), pm.height()))

    # 气泡用**真实额度数据**渲染（能直接看出排版和文案对不对）
    ctl._quota = None
    try:
        from mimo_quota import QuotaClient
        ctl._quota = QuotaClient().get(force=True)
        print("  额度来源: %s" % ctl._quota.get("source"))
    except Exception as e:
        print("  额度读取失败: %s" % e)
    b = BubbleWindow()
    ctl.bubble = b
    ctl._render_bubble()
    b.pop_in()
    b.setAlpha(1.0)
    app.processEvents()
    bp = os.path.join(outdir, "bubble.png")
    b.grab().save(bp)
    print("  气泡 -> %s (%dx%d)" % (bp, b.width(), b.height()))

    # 彩蛋贴纸气泡（每张都渲染一张，能一次看到全部表情包）
    try:
        from mimo_egg import EggTracker
        pack = EggTracker()
        if len(pack):
            b2 = BubbleWindow()
            for item in pack.items:
                pm = pack.pixmap(item)
                if pm.isNull():
                    continue
                mood = item.get("mood", "idle")
                b2.set_sticker(pm, title="",
                               sub="%s %s" % (STATE_EMOJI.get(mood, "✦"),
                                              STATE_LABEL.get(mood, mood)),
                               footer="再点桌宠收起 · 5 秒后自动收起",
                               dark=bool(item.get("dark")))
                b2.pop_in()
                b2.setAlpha(1.0)
                app.processEvents()
                sp = os.path.join(outdir, "egg-%s.png" % item["file"]
                                  .replace(".png", ""))
                b2.grab().save(sp)
                print("  彩蛋 -> %s (%dx%d)"
                      % (sp, b2.width(), b2.height()))
            b2.close_now()
    except Exception as e:
        print("  彩蛋渲染失败: %s" % e)
    print("SELFTEST OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
