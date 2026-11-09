#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""dbg_login.py — 看 SSO 返回的登录页到底是什么（风控？验证？）。

用法: python dbg_login.py
"""
import json
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"D:\桌面宠物\pet")

import mimo_quota as Q

PLATFORM = "https://platform.xiaomimimo.com"


def main():
    cred = Q.load_cache() or {}
    c1 = {k: v for k, v in cred.items() if k != "platform_cookies"}
    opener, jar = Q._build_opener(c1)
    st, url, body = Q._get(opener, PLATFORM + "/api/v1/usage")
    lu = json.loads(body).get("loginUrl")
    st2, url2, body2 = Q._get(opener, lu)
    print("HTTP %s  final=%s  len=%d" % (st2, url2, len(body2 or "")))

    html = body2 or ""
    # 去掉 script/style
    txt = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", html)
    txt = re.sub(r"(?s)<[^>]+>", " ", txt)
    txt = re.sub(r"\s+", " ", txt).strip()
    print("\n-- 可见文本 --")
    print(txt[:1200])

    print("\n-- 关键词 --")
    for kw in ("扫码", "验证", "安全", "风控", "登录", "账号", "密码",
               "captcha", "verify", "login", "account"):
        if kw in html:
            i = html.find(kw)
            print("  %-10s @%d : %s" % (kw, i, html[max(0, i - 160):i + 160]
                                         .replace("\n", " ")[:320]))

    print("\n-- script 里的配置 --")
    for m in re.finditer(r"(?s)<script[^>]*>(.*?)</script>", html):
        s = m.group(1).strip()
        if s and len(s) < 3000:
            print("  " + s[:1200].replace("\n", " "))


if __name__ == "__main__":
    main()
