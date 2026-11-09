#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""read_xiaomi_cookies.py — 读 xiaomi-account 分区的 cookie 库（含多种解锁策略）。"""
import ctypes
import os
import shutil
import sqlite3
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from ctypes import wintypes

UD = os.path.join(os.environ["APPDATA"], "Xiaomi MiMo")
DB = os.path.join(UD, "Partitions", "xiaomi-account", "Network", "Cookies")

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
GENERIC_READ = 0x80000000
FILE_SHARE_READ = 0x1
FILE_SHARE_WRITE = 0x2
FILE_SHARE_DELETE = 0x4
OPEN_EXISTING = 3
FILE_ATTRIBUTE_NORMAL = 0x80
INVALID_HANDLE_VALUE = wintypes.HANDLE(-1).value

kernel32.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                 ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD,
                                 wintypes.HANDLE]
kernel32.CreateFileW.restype = wintypes.HANDLE
kernel32.ReadFile.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD,
                              ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p]


def raw_read(path):
    """用 Win32 直接读，共享模式放宽，绕过 sqlite 的锁。"""
    h = kernel32.CreateFileW(path, GENERIC_READ,
                              FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
                              None, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, None)
    if h == INVALID_HANDLE_VALUE:
        raise ctypes.WinError(ctypes.get_last_error())
    buf = bytearray()
    chunk = ctypes.create_string_buffer(1 << 20)
    got = wintypes.DWORD(0)
    try:
        while True:
            if not kernel32.ReadFile(h, chunk, len(chunk), ctypes.byref(got), None):
                break
            if got.value == 0:
                break
            buf += chunk.raw[:got.value]
    finally:
        kernel32.CloseHandle(h)
    return bytes(buf)


def copy_via_guarded(path):
    """CreateFile 打开 -> 读 -> 写临时文件。"""
    data = raw_read(path)
    tmp = os.path.join(tempfile.gettempdir(), "mimo-xc-%d.db" % os.getpid())
    with open(tmp, "wb") as f:
        f.write(data)
    return tmp


def dump(path):
    print("=" * 70)
    print(path)
    if not os.path.isfile(path):
        print("  不存在")
        return
    print("  大小:", os.path.getsize(path))
    tmp = None
    try:
        try:
            shutil.copyfile(path, path + ".probe")
            tmp = path + ".probe"
        except Exception as e:
            print("  直接复制失败:", e)
            try:
                tmp = copy_via_guarded(path)
                print("  Win32 共享读成功")
            except Exception as e2:
                print("  Win32 共享读也失败:", e2)
                return
        con = sqlite3.connect(tmp)
        cur = con.cursor()
        tabs = [r[0] for r in cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        print("  表:", tabs)
        if "cookies" in tabs:
            rows = cur.execute(
                "SELECT host_key, name, path, expires_utc, length(encrypted_value),"
                " length(value), is_secure, is_httponly FROM cookies").fetchall()
            print("  cookies 行数:", len(rows))
            for r in rows[:60]:
                print("    %-34s %-22s enc=%-5s plain=%-5s sec=%s http=%s"
                      % (r[0], r[1], r[4], r[5], r[6], r[7]))
        con.close()
    finally:
        if tmp and os.path.isfile(tmp):
            try:
                os.remove(tmp)
            except Exception:
                pass


for p in (DB, os.path.join(UD, "Network", "Cookies"),
          os.path.join(UD, "Partitions", "rp-browser", "Network", "Cookies")):
    dump(p)
