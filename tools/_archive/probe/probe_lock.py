#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""probe_lock.py — 试各种共享模式打开被 Chromium 锁住的 cookie 库。

用法: python probe_lock.py
"""
import ctypes
import os
import sqlite3
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"D:\桌面宠物\pet")

import mimo_quota as Q

GENERIC_READ = 0x80000000
OPEN_EXISTING = 3
FILE_SHARE_READ = 0x1
FILE_SHARE_WRITE = 0x2
FILE_SHARE_DELETE = 0x4
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
k32.CreateFileW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32,
                            ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32,
                            ctypes.c_void_p]
k32.CreateFileW.restype = ctypes.c_void_p
k32.CloseHandle.argtypes = [ctypes.c_void_p]
k32.CloseHandle.restype = ctypes.c_bool

MODES = [
    ("RW (无 DELETE)", FILE_SHARE_READ | FILE_SHARE_WRITE),
    ("R  (无 WRITE/DELETE)", FILE_SHARE_READ),
    ("RW+D", FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE),
]


def try_open(path, share):
    h = k32.CreateFileW(path, GENERIC_READ, share, None, OPEN_EXISTING,
                        0x80, None)          # FILE_ATTRIBUTE_NORMAL
    if h == INVALID_HANDLE_VALUE or h is None:
        return None, ctypes.get_last_error()
    k32.CloseHandle(ctypes.c_void_p(h))
    return h, 0


def main():
    for path in Q.cookie_db_paths():
        print("\n=== %s ===" % path)
        for tag, share in MODES:
            h, err = try_open(path, share)
            if h is None:
                print("  %-22s 打不开  err=%d (%s)"
                      % (tag, err, ctypes.FormatError(err)))
                continue
            print("  %-22s 能打开" % tag)
            # 试着直接当 sqlite 读（immutable=1 绕过锁）
            try:
                con = sqlite3.connect("file:%s?immutable=1" % path.replace("\\", "/"),
                                      uri=True)
                rows = con.execute("SELECT host_key, name, length(value), "
                                   "length(encrypted_value) FROM cookies").fetchall()
                con.close()
                print("      immutable 读取成功: %d 条" % len(rows))
                for r in rows[:25]:
                    print("        %-40s %-28s plain=%s enc=%s" % r)
            except Exception as e:
                print("      immutable 读取失败: %s" % e)
            break


if __name__ == "__main__":
    main()
