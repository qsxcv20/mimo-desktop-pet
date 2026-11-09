#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_pet_live.py — 端到端验证：给 MiMo 发一轮对话，观察桌宠表情是否随事件自动切换，
并在每次切换时截图取证。

    python verify_pet_live.py
"""
import json
import os
import sys
import time
import urllib.request

sys.path.insert(0, r"D:\桌面宠物\pet")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from mimo_link import MimoClient, load_credentials

PET_DIR = r"D:\桌面宠物\pet"
STATUS = os.path.join(PET_DIR, "pet_status.json")
OUT = r"D:\桌面宠物\_mimo\live"
os.makedirs(OUT, exist_ok=True)

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QGuiApplication


def status():
    try:
        with open(STATUS, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def shot(tag):
    app = QApplication.instance() or QApplication(sys.argv)
    pm = QGuiApplication.primaryScreen().grabWindow(0)
    w, h = 560, 460
    x, y = max(0, pm.width() - w), max(0, pm.height() - h)
    pm = pm.copy(x, y, w, h)
    p = os.path.join(OUT, "live-%s.png" % tag)
    pm.save(p)
    return p


def main():
    c = MimoClient()
    s = c.active_session()
    sid, d = s["id"], s.get("directory")
    print("目标会话:", sid, "|", s.get("title"))

    before = status()
    print("桌宠当前:", before.get("state"), "| pid", before.get("pid"))
    p = shot("00-before")
    print("  截图 ->", p)

    port, token = load_credentials()
    body = json.dumps({
        "message": "请用大约 300 个汉字介绍一下你自己能做什么，要具体，不要用列表。",
        "model": "minimax-cn/MiniMax-M3.1-Flash",
        "dir": d,
    }).encode("utf-8")
    req = urllib.request.Request(
        "http://127.0.0.1:%d/v1/sessions/%s/turns" % (port, sid),
        data=body, method="POST",
        headers={"Authorization": "Bearer " + token,
                 "Host": "127.0.0.1:%d" % port,
                 "Content-Type": "application/json"})
    print("发送 turn:", urllib.request.urlopen(req, timeout=25).read().decode())

    seen = []
    last = None
    t0 = time.time()
    while time.time() - t0 < 75:
        time.sleep(0.4)
        st = status()
        cur = st.get("state")
        if cur != last:
            last = cur
            seen.append((round(time.time() - t0, 1), cur, st.get("last_event")))
            p = shot("%02d-%s" % (len(seen), cur))
            print("  t=+%-5s 表情 -> %-6s (事件 %s)  截图 %s"
                  % (seen[-1][0], cur, st.get("last_event"), os.path.basename(p)))
        if len(seen) >= 4 and time.time() - t0 > 40:
            break

    print()
    print("表情切换时间线:")
    for t, s2, ev in seen:
        print("   +%-6s %-6s  <- %s" % (t, s2, ev))
    final = status()
    print()
    print("最终:", final.get("state"), "| 连接:", final.get("connected"),
          "| 会话:", final.get("session"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
