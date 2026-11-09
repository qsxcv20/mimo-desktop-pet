#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""probe_sign.py — 穷举「签名请求头」的名称。

签名值来自平台 401 响应里 loginUrl 的 callback 参数 sign=...。

用法: python probe_sign.py
"""
import json
import sys
import urllib.parse
import urllib.request
import urllib.error

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"D:\桌面宠物\pet")

import mimo_quota as Q

PLATFORM = "https://platform.xiaomimimo.com"

NAMES = [
    "Sign", "sign", "X-Sign", "X-Signature", "Signature",
    "X-Mimo-Sign", "X-Mimo-Signature", "X-Mimo-Token",
    "X-Platform-Sign", "X-Api-Sign", "X-Auth-Sign", "X-Mi-Sign",
    "Mimo-Sign", "X-SSO-Sign", "X-Service-Sign", "X-Request-Sign",
    "X-Sign-Value", "X-Token-Sign", "X-Mimo-Auth-Sign",
    "X-Account-Sign", "X-Client-Sign", "clientSign", "x-client-sign",
]


def get_sign():
    opener, jar = Q._build_opener({"passToken": "", "userId": "", "cUserId": ""})
    st, url, body = Q._get(opener, PLATFORM + "/api/v1/usage")
    lu = json.loads(body).get("loginUrl")
    q = urllib.parse.parse_qs(urllib.parse.urlparse(lu).query)
    cb = q.get("callback", [""])[0]
    cbq = urllib.parse.parse_qs(urllib.parse.urlparse(cb).query)
    return cbq.get("sign", [""])[0], lu


def main():
    sign, lu = get_sign()
    print("sign = %r" % sign)
    if not sign:
        print("拿不到 sign，退出")
        return

    cred = Q.load_cache()
    c1 = {k: v for k, v in cred.items() if k != "platform_cookies"}

    # 先做一次完整 SSO，拿到 serviceToken 等票据（用带平台 cookie 的 opener）
    opener, jar = Q._build_opener(c1)
    Q._get(opener, lu)          # 跟随重定向到 followup（会 403，无妨）
    pc = {}
    for c in jar:
        if c.name.startswith("api-platform_") or c.name == "userId":
            pc[c.name] = c.value
    print("票据: %s" % list(pc.keys()))

    base_hdr = dict(Q.HDR)
    base_hdr["X-Client-Version"] = "26.1102.21158"

    for name in NAMES:
        hdr = dict(base_hdr)
        hdr[name] = sign
        opener2, jar2 = Q._build_opener(c1)
        for n, v in pc.items():
            jar2.set_cookie(Q._RawCookie(n, v, ".platform.xiaomimimo.com"))
        req = urllib.request.Request(
            PLATFORM + "/api/v1/usage?userId=3113399232", headers=hdr)
        try:
            with opener2.open(req, timeout=15) as r:
                body = r.read(300).decode("utf-8", "replace")
                print("  ★ %-20s -> HTTP %s  %s" % (name, r.status, body[:120]))
                break
        except urllib.error.HTTPError as e:
            body = e.read(300).decode("utf-8", "replace")
            if "SIGN_MISSING" in body:
                print("  . %-20s -> 仍缺签名" % name)
                continue
            print("  ★ %-20s -> HTTP %s  %s" % (name, e.code, body[:200]))
            break
        except Exception as e:
            print("  ! %-20s -> %s" % (name, e))
    else:
        print("\n所有候选头名都没命中")


if __name__ == "__main__":
    main()
