#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
mimo_host.py — 把桌宠「塞进」MiMo 应用窗口里。

思路（不改 MiMo 任何文件，避开 runtime-res 的 sha256 校验）：
  1. 找到 MiMo 的浏览器主窗口（class=Chrome_WidgetWin_1, title='Xiaomi MiMo'）
  2. 枚举它的子窗口，看清 Chromium 的渲染子窗口在哪
  3. 两种承载模式：
       mode='child'  —— Win32 SetParent 把桌宠窗口变成 MiMo 的子窗口，
                         坐标改为 MiMo 客户区坐标。真正「在窗口里面」。
       mode='overlay' —— 独立顶层透明窗，每帧跟随 MiMo 窗口位置并夹在窗口矩形内。
                         渲染层永远盖不住它，稳。视觉上一样是「被限制在窗口内」。

两种模式都会：
  * MiMo 最小化/隐藏 -> 桌宠跟着隐藏
  * MiMo 窗口移动/缩放 -> 桌宠跟随
  * 桌宠只能在 MiMo 客户区内活动（贴边吸附也基于客户区）
"""

import ctypes
import ctypes.wintypes as wt

user32 = ctypes.WinDLL("user32", use_last_error=True)
try:
    shcore = ctypes.WinDLL("shcore")
    GetDpiForWindow = shcore.GetDpiForWindow
except Exception:  # pragma: no cover
    GetDpiForWindow = None
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)

user32.SetParent.argtypes = [wt.HWND, wt.HWND]
user32.SetParent.restype = wt.HWND
user32.GetParent.argtypes = [wt.HWND]
user32.GetParent.restype = wt.HWND
user32.IsWindow.argtypes = [wt.HWND]
user32.IsWindow.restype = wt.BOOL
user32.IsWindowVisible.argtypes = [wt.HWND]
user32.IsWindowVisible.restype = wt.BOOL
user32.IsIconic.argtypes = [wt.HWND]
user32.IsIconic.restype = wt.BOOL
user32.GetWindowRect.argtypes = [wt.HWND, ctypes.POINTER(wt.RECT)]
user32.GetWindowRect.restype = wt.BOOL
user32.GetClientRect.argtypes = [wt.HWND, ctypes.POINTER(wt.RECT)]
user32.GetClientRect.restype = wt.BOOL
user32.ClientToScreen.argtypes = [wt.HWND, ctypes.POINTER(wt.POINT)]
user32.ClientToScreen.restype = wt.BOOL
user32.ScreenToClient.argtypes = [wt.HWND, ctypes.POINTER(wt.POINT)]
user32.ScreenToClient.restype = wt.BOOL
user32.GetWindowLongPtrW.argtypes = [wt.HWND, ctypes.c_int]
user32.GetWindowLongPtrW.restype = ctypes.c_longlong
user32.SetWindowLongPtrW.argtypes = [wt.HWND, ctypes.c_int, ctypes.c_longlong]
user32.SetWindowLongPtrW.restype = ctypes.c_longlong
user32.SetWindowPos.argtypes = [wt.HWND, wt.HWND, ctypes.c_int, ctypes.c_int,
                                ctypes.c_int, ctypes.c_int, wt.UINT]
user32.SetWindowPos.restype = wt.BOOL
user32.GetWindowTextW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]
user32.GetWindowTextLengthW.argtypes = [wt.HWND]
user32.GetWindowTextLengthW.restype = ctypes.c_int
user32.GetClassNameW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]
user32.GetClassNameW.restype = ctypes.c_int
user32.GetWindowThreadProcessId.argtypes = [wt.HWND, ctypes.POINTER(wt.DWORD)]
user32.GetWindowThreadProcessId.restype = wt.DWORD
user32.GetForegroundWindow.restype = wt.HWND
user32.GetWindow.argtypes = [wt.HWND, wt.UINT]
user32.GetWindow.restype = wt.HWND
user32.GetDesktopWindow.restype = wt.HWND
user32.RedrawWindow.argtypes = [wt.HWND, ctypes.c_void_p, ctypes.c_void_p, wt.UINT]
user32.RedrawWindow.restype = wt.BOOL
user32.GetWindowPlacement.argtypes = [wt.HWND, ctypes.c_void_p]
user32.GetWindowPlacement.restype = wt.BOOL

GWL_STYLE = -16
GWL_EXSTYLE = -20
GWLP_HWNDPARENT = -8
WS_CHILD = 0x40000000
WS_POPUP = 0x80000000
WS_CAPTION = 0x00C00000
WS_THICKFRAME = 0x00040000
WS_MINIMIZEBOX = 0x00020000
WS_MAXIMIZEBOX = 0x00010000
WS_SYSMENU = 0x00080000
WS_CLIPCHILDREN = 0x02000000
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000
WS_EX_APPWINDOW = 0x00040000
WS_EX_TOPMOST = 0x00000008

SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010
SWP_FRAMECHANGED = 0x0020
SWP_SHOWWINDOW = 0x0040
SWP_HIDEWINDOW = 0x0080
SWP_NOOWNERZORDER = 0x0200
HWND_TOP = 0
HWND_BOTTOM = 1
HWND_TOPMOST = -1
HWND_NOTOPMOST = -2

RDW_INVALIDATE = 0x0001
RDW_ERASE = 0x0004
RDW_ALLCHILDREN = 0x0080
RDW_UPDATENOW = 0x0100

WINDOWPLACEMENT = ctypes.Structure if False else None


class WINDOWPLACEMENT(ctypes.Structure):
    _fields_ = [("length", ctypes.c_uint),
                ("flags", ctypes.c_uint),
                ("showCmd", ctypes.c_uint),
                ("ptMinPosition", wt.POINT),
                ("ptMaxPosition", wt.POINT),
                ("rcNormalPosition", wt.RECT)]


# ---------------------------------------------------------------- 窗口枚举

def _text(hwnd):
    n = user32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(n + 2)
    user32.GetWindowTextW(hwnd, buf, n + 2)
    return buf.value


def _cls(hwnd):
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buf, 256)
    return buf.value


def _pid(hwnd):
    pid = wt.DWORD(0)
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value


def _rect(hwnd):
    r = wt.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    return (r.left, r.top, r.right, r.bottom)


def _client_rect(hwnd):
    r = wt.RECT()
    user32.GetClientRect(hwnd, ctypes.byref(r))
    return (r.left, r.top, r.right, r.bottom)


def _style(hwnd):
    return user32.GetWindowLongPtrW(hwnd, GWL_STYLE) & 0xFFFFFFFF


def _exstyle(hwnd):
    return user32.GetWindowLongPtrW(hwnd, GWL_EXSTYLE) & 0xFFFFFFFF


WNDENUMPROC = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)


def enum_top():
    out = []

    def cb(hwnd, _l):
        out.append(hwnd)
        return True

    user32.EnumWindows(WNDENUMPROC(cb), 0)
    return out


def enum_children(parent):
    out = []

    def cb(hwnd, _l):
        out.append(hwnd)
        return True

    user32.EnumChildWindows(parent, WNDENUMPROC(cb), 0)
    return out


def is_mimo_process(pid):
    """判断 pid 是否属于 MiMo.exe。"""
    try:
        import psutil
        try:
            p = psutil.Process(pid)
            return p.name().lower().startswith("xiaomi mimo") or \
                   p.name().lower() == "mimo.exe"
        except Exception:
            return False
    except Exception:
        return False


# ---------------------------------------------------------------- MiMo 主窗口

def _normal_size(hwnd):
    """窗口「还原后」的尺寸。最小化时 GetWindowRect 只给出 (-32000,...) 哨兵值。"""
    wp = WINDOWPLACEMENT()
    wp.length = ctypes.sizeof(WINDOWPLACEMENT)
    try:
        if user32.GetWindowPlacement(hwnd, ctypes.byref(wp)):
            r = wp.rcNormalPosition
            w = r.right - r.left
            h = r.bottom - r.top
            if w > 0 and h > 0:
                return w, h
    except Exception:
        pass
    return 0, 0


def find_mimo_window(timeout=30.0, poll=0.5, include_hidden=False):
    """找 MiMo 的浏览器主窗口。返回 hwnd 或 None。

    判据：class == 'Chrome_WidgetWin_1'，有 WS_CAPTION，进程名像 MiMo。
    标题可能是 'Xiaomi MiMo'（随会话标题变），所以不硬匹配标题。
    include_hidden=True 时把收进托盘（hide）的窗口也算进来。

    ⚠️ 窗口最小化时 GetWindowRect 只返回 (-32000,-32000,-31840,-31972) 这种
    哨兵矩形（160x28），按这个尺寸过滤会把窗口误判成「不是主窗口」。
    所以尺寸判断要用 GetWindowPlacement 给出的还原尺寸。
    """
    import time
    t0 = time.time()
    best = None
    while True:
        for hwnd in enum_top():
            if not include_hidden and not user32.IsWindowVisible(hwnd):
                continue
            if _cls(hwnd) != "Chrome_WidgetWin_1":
                continue
            st = _style(hwnd)
            if not (st & WS_CAPTION):
                continue
            pid = _pid(hwnd)
            if not is_mimo_process(pid):
                continue
            r = _rect(hwnd)
            w = r[2] - r[0]
            h = r[3] - r[1]
            if w < 200 or h < 100:
                nw, nh = _normal_size(hwnd)
                if nw:
                    w, h = nw, nh
            if w < 200:
                continue
            best = hwnd
            return hwnd
        if time.time() - t0 >= timeout:
            return best
        time.sleep(poll)


def describe(hwnd):
    r = _rect(hwnd)
    cr = _client_rect(hwnd)
    return {
        "hwnd": hex(hwnd),
        "pid": _pid(hwnd),
        "class": _cls(hwnd),
        "title": _text(hwnd),
        "rect": r,
        "client": cr,
        "visible": bool(user32.IsWindowVisible(hwnd)),
        "minimized": bool(user32.IsIconic(hwnd)),
    }


def child_tree(hwnd):
    """列出 MiMo 主窗口的子窗口（含类名/样式/矩形），用来判断渲染层。"""
    out = []
    for c in enum_children(hwnd):
        st = _style(c)
        out.append({
            "hwnd": hex(c),
            "class": _cls(c),
            "text": _text(c),
            "rect": _rect(c),
            "child": bool(st & WS_CHILD),
            "visible": bool(user32.IsWindowVisible(c)),
            "ex": hex(_exstyle(c)),
            "style": hex(st),
        })
    return out


# ---------------------------------------------------------------- DPI

def dpi_for(hwnd):
    if GetDpiForWindow is not None:
        try:
            d = GetDpiForWindow(hwnd)
            if d:
                return float(d)
        except Exception:
            pass
    try:
        dc = user32.GetDC(0)
        d = gdi32.GetDeviceCaps(dc, 88)  # LOGPIXELSX
        user32.ReleaseDC(0, dc)
        return float(d or 96)
    except Exception:
        return 96.0


def scale_for(hwnd):
    return dpi_for(hwnd) / 96.0


# ---------------------------------------------------------------- 坐标

def client_to_screen(hwnd, x, y):
    p = wt.POINT(int(x), int(y))
    user32.ClientToScreen(hwnd, ctypes.byref(p))
    return (p.x, p.y)


def screen_to_client(hwnd, x, y):
    p = wt.POINT(int(x), int(y))
    user32.ScreenToClient(hwnd, ctypes.byref(p))
    return (p.x, p.y)


def client_size(hwnd):
    r = _client_rect(hwnd)
    return (r[2] - r[0], r[3] - r[1])


def is_minimized(hwnd):
    return bool(user32.IsIconic(hwnd))


def is_shown(hwnd):
    return bool(user32.IsWindowVisible(hwnd))


# ---------------------------------------------------------------- 嵌入

def make_child(pet_hwnd, parent_hwnd):
    """把 pet_hwnd 变成 parent_hwnd 的子窗口。返回是否成功。"""
    if not parent_hwnd or not user32.IsWindow(parent_hwnd):
        return False
    # 去掉 WS_POPUP，加上 WS_CHILD
    st = user32.GetWindowLongPtrW(pet_hwnd, GWL_STYLE)
    st = (st & ~WS_POPUP) | WS_CHILD
    user32.SetWindowLongPtrW(pet_hwnd, GWL_STYLE, st)
    ex = user32.GetWindowLongPtrW(pet_hwnd, GWL_EXSTYLE)
    ex |= WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE
    user32.SetWindowLongPtrW(pet_hwnd, GWL_EXSTYLE, ex)
    user32.SetParent(pet_hwnd, parent_hwnd)
    return True


def detach_to_top(pet_hwnd):
    """从父窗口摘出来变回顶层窗口。"""
    st = user32.GetWindowLongPtrW(pet_hwnd, GWL_STYLE)
    st = (st & ~WS_CHILD) | WS_POPUP
    user32.SetWindowLongPtrW(pet_hwnd, GWL_STYLE, st)
    ex = user32.GetWindowLongPtrW(pet_hwnd, GWL_EXSTYLE)
    ex &= ~WS_EX_TOOLWINDOW
    user32.SetWindowLongPtrW(pet_hwnd, GWL_EXSTYLE, ex)
    user32.SetParent(pet_hwnd, None)


def raise_child(pet_hwnd):
    """在同级子窗口里置顶（Chromium 重建渲染层后需要重刷）。"""
    user32.SetWindowPos(pet_hwnd, HWND_TOP, 0, 0, 0, 0,
                        SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW)


def topmost(pet_hwnd, on=True):
    user32.SetWindowPos(pet_hwnd, HWND_TOPMOST if on else HWND_NOTOPMOST,
                        0, 0, 0, 0,
                        SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)


def move_child(pet_hwnd, x, y, w=None, h=None):
    user32.SetWindowPos(pet_hwnd, HWND_TOP, int(x), int(y),
                        int(w) if w else 0, int(h) if h else 0,
                        SWP_NOACTIVATE | SWP_SHOWWINDOW)


def move_top(pet_hwnd, sx, sy, w=None, h=None):
    user32.SetWindowPos(pet_hwnd, HWND_TOPMOST, int(sx), int(sy),
                        int(w) if w else 0, int(h) if h else 0,
                        SWP_NOACTIVATE | SWP_SHOWWINDOW)


def force_redraw(hwnd):
    user32.RedrawWindow(hwnd, None, None,
                         RDW_INVALIDATE | RDW_ERASE | RDW_ALLCHILDREN | RDW_UPDATENOW)


def show_window(hwnd):
    user32.SetWindowPos(hwnd, HWND_TOP, 0, 0, 0, 0,
                        SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW)


def hide_window(hwnd):
    user32.SetWindowPos(hwnd, HWND_TOP, 0, 0, 0, 0,
                        SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_HIDEWINDOW)


def foreground():
    return user32.GetForegroundWindow()


# ---------------------------------------------------------------- 显示 MiMo


def _mimo_main_windows():
    """所有 MiMo 主窗口（含收进托盘、被 hide 的）。"""
    out = []
    for hwnd in enum_top():
        try:
            if _cls(hwnd) != "Chrome_WidgetWin_1":
                continue
            if not (_style(hwnd) & WS_CAPTION):
                continue
            if not is_mimo_process(_pid(hwnd)):
                continue
            r = _rect(hwnd)
            if (r[2] - r[0]) < 200:
                continue
            out.append(hwnd)
        except Exception:
            continue
    return out


def show_mimo_window(timeout=12.0, poll=0.5):
    """把 MiMo 主窗口显示出来。返回 True 表示已经有可见窗口。

    坑：从计划任务 / 快捷方式启动 MiMo 时，Electron 的窗口可能是隐藏的
    （进程在、窗口不在）。用户看到的就是「MiMo 开着但什么都没有」——
    而桌宠是 owned window，owner 隐藏它也跟着隐藏，等于两头都看不见。

    ⚠️ ShowWindow 的第一个参数是 HWND（指针宽）。不声明 argtypes 的话
    ctypes 默认按 c_int 传，64 位下句柄会被截断 -> 调用没效果。
    """
    import time
    try:
        user32.ShowWindow.argtypes = [wt.HWND, ctypes.c_int]
        user32.ShowWindow.restype = wt.BOOL
    except Exception:
        pass

    t0 = time.time()
    while True:
        wins = _mimo_main_windows()
        for h in wins:
            if user32.IsWindowVisible(h):
                return True
        for h in wins:
            try:
                user32.ShowWindow(h, 5)          # SW_SHOW
                time.sleep(0.5)
                if user32.IsWindowVisible(h):
                    return True
                user32.ShowWindow(h, 9)          # SW_RESTORE
                time.sleep(0.5)
                if user32.IsWindowVisible(h):
                    return True
            except Exception:
                continue
        if time.time() - t0 >= timeout:
            return False
        time.sleep(poll)
