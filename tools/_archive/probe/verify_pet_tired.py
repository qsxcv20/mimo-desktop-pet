#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_pet_tired.py — 用一个不可用的模型触发 MiMo 的 ui(kind=error) 事件，
验证桌宠会切到 tired 表情，并截图取证。
"""
import json
import os
import sys
import time
import urllib.request

sys.path.insert(0, r"D:\桌面宠物\pet")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from mimo_link import MimoClient, load_credentials
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QGuiApplication

PET_DIR = r"D:\桌面宠物\pet"
STATUS = os.path.join(PET_DIR, "pet_status.json")
OUT = r"D:\桌面宠物\_mimo\live"
os.makedirs(OUT, exist_ok=True)


def status():
    try:
        with open(STATUS, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def shot(tag):
    app = QApplication.instance() or QApplication(sys.argv)
    pm = QGuiApplication.primaryScreen().grabWindow(0)
    w, h = 560, 460
    pm = pm.copy(max(0, pm.width() - w), max(0, pm.height() - h), w, h)
    p = os.path.join(OUT, "live-%s.png" % tag)
    pm.save(p)
    return p


def main():
    c = MimoClient()
    s = c.active_session()
    sid, d = s["id"], s.get("directory")
    port, token = load_credentials()

    # 这个模型已不可用 -> 会触发 ui(kind=error)
    body = json.dumps({"message": "触发错误以验证 tired 表情",
                       "model": "minimax-cn/MiniMax-M2.1-highspeed",
                       "dir": d}).encode("utf-8")
    req = urllib.request.Request(
        "http://127.0.0.1:%d/v1/sessions/%s/turns" % (port, sid),
        data=body, method="POST",
        headers={"Authorization": "Bearer " + token,
                 "Host": "127.0.0.1:%d" % port,
                 "Content-Type": "application/json"})
    print("发送(坏模型) turn:", urllib.request.urlopen(req, timeout=25).read().decode())

    seen, last, t0 = [], None, time.time()
    while time.time() - t0 < 45:
        time.sleep(0.35)
        st = status()
        cur = st.get("state")
        if cur != last:
            last = cur
            seen.append((round(time.time() - t0, 1), cur, st.get("last_event")))
            p = shot("%02d-%s" % (len(seen), cur))
            print("  t=+%-5s 表情 -> %-6s (事件 %s)  %s"
                  % (seen[-1][0], cur, st.get("last_event"), os.path.basename(p)))
        if any(s2 == "tired" for _, s2, _ in seen) and len(seen) >= 3:
            break
    print()
    for t, s2, ev in seen:
        print("   +%-6s %-6s <- %s" % (t, s2, ev))
    return 0


if __name__ == "__main__":
    sys.exit(main())
