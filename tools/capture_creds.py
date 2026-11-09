#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""capture_creds.py — 在 MiMo 关闭的窗口期，把账号分区的**全部** cookie 抓下来。

为什么需要全量：
    MiMo 桌面自己查额度用的是
        GET https://mimo-server-cn.xiaomimimo.com/api/user/usage
    走的是 Electron session（partition "persist:xiaomi-account"）的 cookie，
    主进程代码 ru() 只加 UA + X-Client-Version，**不涉及任何签名头**。
    所以只要把该 partition 的 cookie 复制出来，就能直接复现这个请求。

Chromium 运行时会对 cookie 库加排他锁（WinError 32），所以必须：
    关掉 MiMo -> 读库 -> 重启 MiMo

用法:
    python capture_creds.py            # 抓 + 重启
    python capture_creds.py --no-restart
"""
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass  # pythonw.exe 下 sys.stdout 是 None
sys.path.insert(0, r"D:\桌面宠物\pet")
sys.path.insert(0, r"D:\桌面宠物\tools")

import mimo_quota as Q
import mimo_host as H

CRED_CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "..", "pet", "quota_cred.json")

INTEREST = ("xiaomi", "mimo", "mi.com", "xiaomimimo")


def db_candidates():
    base = Q.MIMO_UD
    out = []
    default = os.path.join(base, "Network", "Cookies")
    if os.path.isfile(default):
        out.append(("default", default))
    parts = os.path.join(base, "Partitions")
    if os.path.isdir(parts):
        for name in sorted(os.listdir(parts)):
            p = os.path.join(parts, name, "Network", "Cookies")
            if os.path.isfile(p):
                out.append((name, p))
    return out


def dump_db(path):
    """返回 [{host,name,value,domain,path,secure}]（值已解密）。"""
    tmp = os.path.join(tempfile.gettempdir(),
                       "mimo-cap-%d-%d.db" % (os.getpid(), int(time.time())))
    shutil.copyfile(path, tmp)
    rows = []
    try:
        con = sqlite3.connect(tmp)
        cur = con.cursor()
        try:
            rows = cur.execute(
                "SELECT host_key, name, encrypted_value, value, path, "
                "is_secure, expires_utc FROM cookies").fetchall()
        except sqlite3.OperationalError:
            rows = []
        con.close()
    finally:
        try:
            os.remove(tmp)
        except Exception:
            pass

    key = None
    out = []
    for host, name, enc, plain, path, secure, expires in rows:
        h = (host or "").lower()
        if not any(k in h for k in INTEREST):
            continue
        v = plain
        if not v and enc:
            if key is None:
                key = Q.master_key()
            v = Q.decrypt_cookie(enc, key)
        if not v:
            continue
        out.append({"host": host, "name": name, "value": v,
                    "path": path or "/", "secure": bool(secure),
                    "expires": expires})
    return out


def close_mimo():
    host = H.find_mimo_window(timeout=3, include_hidden=True)
    if host:
        import ctypes
        from ctypes import wintypes as wt
        H.user32.PostMessageW.argtypes = [wt.HWND, ctypes.c_uint,
                                          ctypes.c_ulonglong, ctypes.c_longlong]
        H.user32.PostMessageW.restype = wt.BOOL
        H.user32.PostMessageW(host, 0x0010, 0, 0)     # WM_CLOSE
    for _ in range(40):
        time.sleep(0.5)
        if not H.find_mimo_window(timeout=0, include_hidden=True):
            break
    subprocess.run(["taskkill", "/IM", "Xiaomi MiMo.exe", "/F"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2.0)
    print("MiMo 已关闭")


def restart_mimo():
    import restart_mimo
    host = restart_mimo.start_mimo()
    if host:
        print("MiMo 已重启:", hex(host), H.describe(host))
        time.sleep(2.0)
        restart_mimo.check(host)
    return host


def main():
    print("== 1. 关闭 MiMo ==")
    close_mimo()

    print("\n== 2. 读取 cookie 库 ==")
    all_cookies = []
    for tag, path in db_candidates():
        try:
            got = dump_db(path)
        except Exception as e:
            print("  [%s] 读不了: %s" % (tag, e))
            continue
        print("  [%s] %d 条相关 cookie" % (tag, len(got)))
        all_cookies.extend(got)

    # 去重（同名同域留最后一个）
    seen = {}
    for c in all_cookies:
        seen[(c["host"], c["name"])] = c
    all_cookies = list(seen.values())

    by_host = {}
    for c in all_cookies:
        by_host.setdefault(c["host"], []).append(c["name"])
    print("\n== 3. 按域汇总 ==")
    for host, names in sorted(by_host.items()):
        print("  %-46s %s" % (host, ", ".join(sorted(names))))

    cred = {"captured_at": int(time.time()),
            "cookies": all_cookies}
    for k in ("passToken", "userId", "cUserId"):
        for c in all_cookies:
            if c["name"] == k:
                cred[k] = c["value"]
                break
    pc = {c["name"]: c["value"] for c in all_cookies
          if c["name"].startswith("api-platform_")}
    if pc:
        cred["platform_cookies"] = pc

    with open(CRED_CACHE, "w", encoding="utf-8") as f:
        json.dump(cred, f, ensure_ascii=False, indent=2)
    print("\n已写入 %s （%d 条 cookie）" % (os.path.abspath(CRED_CACHE),
                                       len(all_cookies)))

    if "--no-restart" not in sys.argv:
        print("\n== 4. 重启 MiMo ==")
        restart_mimo()


if __name__ == "__main__":
    main()
