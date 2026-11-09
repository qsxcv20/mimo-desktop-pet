#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""shot_cdp.py — 给 CDP target 截图（可用来抓 MiMo 的小米账号登录页）。

用法: python shot_cdp.py [url关键字] [输出文件]
"""
import base64
import json
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"D:\桌面宠物\pet")

import mimo_cdp
from mimo_cdp import MiMoCDP

KEY = sys.argv[1] if len(sys.argv) > 1 else "account.xiaomi.com"
OUT = sys.argv[2] if len(sys.argv) > 2 else r"D:\桌面宠物\_mimo\mimo-login.png"


def main():
    c = MiMoCDP()
    if not c.available():
        print("调试端口没开")
        return 1
    for t in c.targets():
        print("target %-8s %-26s %s" % (t.get("type"), (t.get("title") or "")[:26],
                                       (t.get("url") or "")[:100]))
    tgt = None
    for t in c.targets():
        if t.get("type") == "page" and KEY in (t.get("url") or ""):
            tgt = t
            break
    if not tgt:
        print("没有匹配的 target:", KEY)
        return 1
    print("\n选中: %s\n%s" % (tgt.get("title"), tgt.get("url")))

    import websocket
    ws = websocket.create_connection(tgt["webSocketDebuggerUrl"], timeout=15,
                                     suppress_origin=True)
    try:
        ws.send(json.dumps({"id": 1, "method": "Page.captureScreenshot",
                            "params": {"format": "png"}}))
        while True:
            raw = ws.recv()
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8", "replace")
            msg = json.loads(raw)
            if msg.get("id") == 1:
                data = msg.get("result", {}).get("data")
                if not data:
                    print("截图失败:", json.dumps(msg)[:300])
                    return 1
                open(OUT, "wb").write(base64.b64decode(data))
                print("已保存", OUT)
                return 0
    finally:
        try:
            ws.close()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
