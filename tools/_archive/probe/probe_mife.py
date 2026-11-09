#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""probe_mife.py — 手动拼 Cookie 头，把平台票据直接发给 MiFE 网关。

用法: python probe_mife.py
"""
import json
import sys
import urllib.request
import urllib.error

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"D:\桌面宠物\pet")

import mimo_quota as Q

MIFE = "https://mimo-server-cn.xiaomimimo.com"
USAGE = MIFE + "/api/user/usage"
SUB = MIFE + "/api/user/xiaomi/subscription/self"
ME = MIFE + "/api/user/xiaomi/me"


def raw_get(url, cookie_header, tag, extra=None):
    hdr = dict(Q.HDR)
    hdr["X-Client-Version"] = "26.1102.21158"
    hdr["User-Agent"] = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) "
                         "Chrome/140.0.0.0 Safari/537.36 "
                         "MiMoRuntime/26.1102.21158")
    if cookie_header:
        hdr["Cookie"] = cookie_header
    if extra:
        hdr.update(extra)
    req = urllib.request.Request(url, headers=hdr)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            body = r.read(3000).decode("utf-8", "replace")
            print("  ★ %-42s HTTP %s  %s" % (tag, r.status, body[:260].replace("\n", " ")))
            return r.status, body
    except urllib.error.HTTPError as e:
        body = e.read(600).decode("utf-8", "replace")
        print("  . %-42s HTTP %s  %s" % (tag, e.code, body[:200].replace("\n", " ")))
        return e.code, body
    except Exception as e:
        print("  ! %-42s %s" % (tag, e))
        return None, ""


def main():
    cred = Q.load_cache() or {}
    pc = cred.get("platform_cookies") or {}
    pt = cred.get("passToken") or ""
    uid = cred.get("userId") or "3113399232"

    variants = {
        "platform 票据全量": "; ".join("%s=%s" % (k, v) for k, v in pc.items()),
        "仅 serviceToken": "api-platform_serviceToken=%s" % pc.get("api-platform_serviceToken", ""),
        "serviceToken+slh+ph": "; ".join(
            "%s=%s" % (k, pc.get(k, "")) for k in
            ("api-platform_serviceToken", "api-platform_slh", "api-platform_ph")),
        "serviceToken+userId": "api-platform_serviceToken=%s; userId=%s" % (
            pc.get("api-platform_serviceToken", ""), uid),
        "passToken+userId": "passToken=%s; userId=%s" % (pt, uid),
        "passToken+cUserId+userId": "passToken=%s; cUserId=%s; userId=%s" % (
            pt, cred.get("cUserId", ""), uid),
        "全部拼一起": "; ".join("%s=%s" % (k, v) for k, v in pc.items())
                      + "; passToken=%s; cUserId=%s" % (pt, cred.get("cUserId", "")),
    }

    for url, name in ((USAGE, "/api/user/usage"),
                      (SUB, "/api/user/xiaomi/subscription/self"),
                      (ME, "/api/user/xiaomi/me")):
        print("\n===== %s =====" % name)
        for tag, ch in variants.items():
            raw_get(url, ch, tag)

    # 再试 Bearer / Basic
    print("\n===== Authorization 头尝试 (/api/user/usage) =====")
    for tag, val in (
            ("Bearer passToken", "Bearer " + pt),
            ("Bearer serviceToken", "Bearer " + str(pc.get("api-platform_serviceToken", "")).strip('"')),
            ("Basic userId:passToken", "Basic " + __import__("base64").b64encode(
                ("%s:%s" % (uid, pt)).encode()).decode()),
            ("Basic userId:serviceToken", "Basic " + __import__("base64").b64encode(
                ("%s:%s" % (uid, str(pc.get("api-platform_serviceToken", "")).strip('"'))).encode()).decode()),
    ):
        raw_get(USAGE, None, tag, {"Authorization": val})


if __name__ == "__main__":
    main()
