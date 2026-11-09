#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""test_sids.py — 对多个 sid 试 serviceLogin(_json=true)。

用法: python test_sids.py
"""
import json
import sys
import urllib.error
import urllib.parse
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass  # pythonw.exe 下 sys.stdout 是 None
sys.path.insert(0, r"D:\桌面宠物\pet")

import mimo_quota as Q

ACC = "https://account.xiaomi.com/pass/serviceLogin"
UA = ("miNative PC/Normal Windows_NT/10.0.26200 SDKV/1.0.0 DEVT/PC "
      "DEVS/Windows APP/miaccount_desktop APPV/0.1.0")


def call(sid, pt, uid, cid, extra=None):
    q = {"_locale": "zh_CN", "_snsNone": "true", "sid": sid, "_json": "true"}
    if extra:
        q.update(extra)
    url = ACC + "?" + urllib.parse.urlencode(q)
    hdr = {"User-Agent": UA, "Accept": "application/json",
           "Cookie": "passToken=%s; userId=%s; cUserId=%s" % (pt, uid, cid)}
    req = urllib.request.Request(url, headers=hdr)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, r.read(8000).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read(4000).decode("utf-8", "replace")
    except Exception as e:
        return None, str(e)


def parse(body):
    b = body
    if "&&&START&&&" in b:
        b = b.split("&&&START&&&", 1)[1]
    if "&&&END&&&" in b:
        b = b.split("&&&END&&&", 1)[0]
    try:
        return json.loads(b)
    except Exception:
        return None


def main():
    cred = Q.load_cache() or {}
    pt = cred.get("passToken") or ""
    uid = cred.get("userId") or "3113399232"
    cid = cred.get("cUserId") or ""

    for sid in ("passport", "passportapi", "api-platform", "mi",
                "mimo", "mimo-platform"):
        st, body = call(sid, pt, uid, cid)
        j = parse(body)
        if j:
            print("  sid=%-14s HTTP %s  code=%s  %s  loc=%s"
                  % (sid, st, j.get("code"), (j.get("description") or "")[:24],
                     (j.get("loc") or j.get("location") or "")[:70]))
            if j.get("code") == 0:
                print("      ★ 成功! loc=%s" % (j.get("loc") or "")[:200])
        else:
            print("  sid=%-14s HTTP %s  非JSON: %s" % (sid, st, (body or "")[:120]))


if __name__ == "__main__":
    main()
