#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""cdp_cookies.py — 通过 CDP 导出浏览器实时 cookie，并尝试用 MiMo 自己的 sid=mimopc 换票。

背景：
    quota_cred.json 里缓存的 passToken 已被账号服务器判失效（serviceLogin 返回 70016）。
    但浏览器里 account.xiaomi.com 的会话可能还活着；
    MiMo 自己用的是 sid=mimopc（不是 api-platform），值得单独试一次。

用法: python cdp_cookies.py
"""
import http.cookiejar
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pet"))

from mimo_cdp import MiMoCDP  # noqa: E402

ACC = "https://account.xiaomi.com/pass/serviceLogin"
UA = ("miNative PC/Normal Windows_NT/10.0.26200 SDKV/1.0.0 DEVT/PC "
      "DEVS/Windows APP/miaccount_desktop APPV/0.1.0")


def cdp_cookies():
    """用 CDP 从运行中的浏览器里拿全部 cookie。"""
    import websocket
    c = MiMoCDP()
    tgt = c.pick_login_target() or c.pick_target()
    if not tgt:
        raise RuntimeError("没有可用 target")
    ws = websocket.create_connection(tgt["webSocketDebuggerUrl"], timeout=10,
                                     suppress_origin=True)
    try:
        ws.send(json.dumps({"id": 1, "method": "Storage.getCookies", "params": {}}))
        while True:
            raw = ws.recv()
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8", "replace")
            msg = json.loads(raw)
            if msg.get("id") == 1:
                res = msg.get("result") or {}
                return res.get("cookies") or []
    finally:
        ws.close()


def main():
    try:
        cookies = cdp_cookies()
    except Exception as e:
        print("取 cookie 失败:", e)
        return 1

    print("浏览器 cookie 总数:", len(cookies))
    by_domain = {}
    for ck in cookies:
        by_domain.setdefault(ck.get("domain", "?"), []).append(ck)

    for dom in sorted(by_domain):
        if "xiaomi" in dom or "mimo" in dom:
            names = ", ".join("%s(len=%d)" % (c.get("name"), len(c.get("value") or ""))
                              for c in by_domain[dom])
            print("  %-36s %s" % (dom, names))

    # 取 account.xiaomi.com 的 cookie 拼 header
    jar = http.cookiejar.CookieJar()
    parts = []
    for ck in cookies:
        dom = ck.get("domain", "")
        if "account.xiaomi.com" in dom:
            parts.append("%s=%s" % (ck.get("name"), ck.get("value")))
    cookie_hdr = "; ".join(parts)
    print("\naccount.xiaomi.com cookie 头长度:", len(cookie_hdr))
    print("  包含 passToken:", "passToken" in cookie_hdr)

    for sid in ("mimopc", "api-platform"):
        q = urllib.parse.urlencode({"_locale": "zh_CN", "_snsNone": "true",
                                    "sid": sid, "_json": "true"})
        url = ACC + "?" + q
        hdr = {"User-Agent": UA, "Accept": "application/json",
               "Cookie": cookie_hdr}
        req = urllib.request.Request(url, headers=hdr)
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                body = r.read(4000).decode("utf-8", "replace")
                st = r.status
        except urllib.error.HTTPError as e:
            st, body = e.code, e.read(2000).decode("utf-8", "replace")
        except Exception as e:
            st, body = None, str(e)
        print("\n== serviceLogin sid=%s HTTP %s ==" % (sid, st))
        print(body[:600])

    return 0


if __name__ == "__main__":
    sys.exit(main())
