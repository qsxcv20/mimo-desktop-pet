#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""dbg_sso.py — 逐步打印换票链的 cookie 变化。

用法: python dbg_sso.py
"""
import json
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"D:\桌面宠物\pet")

import mimo_quota as Q

PLATFORM = "https://platform.xiaomimimo.com"


def dump(jar, tag):
    print("  [%s] jar: %s" % (tag, {c.name: str(c.value)[:14] for c in jar}))


def main():
    cred = Q.load_cache() or {}
    c1 = {k: v for k, v in cred.items() if k != "platform_cookies"}
    opener, jar = Q._build_opener(c1)
    dump(jar, "初始")

    st, url, body = Q._get(opener, PLATFORM + "/api/v1/usage")
    print("  第一跳 HTTP %s" % st)
    lu = json.loads(body).get("loginUrl")
    print("  loginUrl: %s" % (lu or "")[:120])
    dump(jar, "第一跳后")

    if not lu:
        return
    st2, url2, body2 = Q._get(opener, lu)
    print("  SSO 之后 HTTP %s" % st2)
    print("  body: %s" % (body2 or "")[:200])
    dump(jar, "SSO后")

    # 再打一次 usage
    st3, url3, body3 = Q._get(opener, PLATFORM + "/api/v1/usage")
    print("  再打 usage HTTP %s  %s" % (st3, (body3 or "")[:120]))


if __name__ == "__main__":
    main()
