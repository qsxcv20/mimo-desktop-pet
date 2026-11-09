#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""test_signed.py — 验证开放平台签名请求。

逆向自 platform.xiaomimimo.com 前端 chunk：
    signKey: GET /api/v1/user/sign-key -> {code:0,data:{signKey,epoch,expiresAt}}
    时钟校准: 响应头 x-server-time
    待签串:  METHOD\nPATH\nSORTED_QUERY\nSHA256(body)\nTIMESTAMP
    X-Sign   = HMAC-SHA256(待签串, signKey)   (hex)
    X-Timestamp = unix 秒（服务端时钟）
    X-Key-Epoch = epoch

用法: python test_signed.py
"""
import hashlib
import hmac
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

PLATFORM = "https://platform.xiaomimimo.com"


def sso(cred):
    """走一次换票链，拿到平台票据。返回 (opener, jar)。"""
    c1 = {k: v for k, v in cred.items() if k != "platform_cookies"}
    opener, jar = Q._build_opener(c1)
    st, url, body = Q._get(opener, PLATFORM + "/api/v1/usage")
    try:
        lu = json.loads(body).get("loginUrl")
    except Exception:
        lu = None
    if lu:
        Q._get(opener, lu)
    pc = {}
    for c in jar:
        if c.name.startswith("api-platform_") or c.name == "userId":
            pc[c.name] = c.value
    return opener, jar, pc


def signed_get(opener, url, method="GET", body="", epoch=None, sign_key=None,
               offset=0.0):
    u = urllib.parse.urlparse(url)
    query = u.query[1:] if u.query.startswith("?") else u.query
    q_sorted = "&".join(sorted([x for x in query.split("&") if x]))
    ts = str(int((__import__("time").time() * 1000 + offset) / 1000))
    body_hash = "" if body == "" else hashlib.sha256(body.encode()).hexdigest()
    msg = "\n".join([method.upper(), u.path, q_sorted, body_hash, ts])
    sign = hmac.new(sign_key.encode(), msg.encode(), hashlib.sha256).hexdigest()
    hdr = dict(Q.HDR)
    hdr["X-Sign"] = sign
    hdr["X-Timestamp"] = ts
    if epoch is not None:
        hdr["X-Key-Epoch"] = str(epoch)
    req = urllib.request.Request(url, headers=hdr, method=method)
    try:
        with opener.open(req, timeout=20) as r:
            return r.status, r.read(3000).decode("utf-8", "replace"), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read(2000).decode("utf-8", "replace"), dict(e.headers or {})


def main():
    cred = Q.load_cache() or {}
    print("== 1. SSO 换票 ==")
    opener, jar, pc = sso(cred)
    print("  票据: %s" % list(pc.keys()))
    if not pc:
        print("  没拿到票据")
        return

    print("\n== 2. 取 sign key ==")
    st, body, hdrs = signed_get.__wrapped__ if False else (None, None, None)
    # sign-key 请求本身不需要签名
    req = urllib.request.Request(PLATFORM + "/api/v1/user/sign-key",
                                 headers=Q.HDR)
    try:
        with opener.open(req, timeout=20) as r:
            sk_raw = r.read(2000).decode("utf-8", "replace")
            st = r.status
            srv = r.headers.get("x-server-time")
            hdrs = dict(r.headers)
    except urllib.error.HTTPError as e:
        sk_raw = e.read(2000).decode("utf-8", "replace")
        st = e.code
        srv = (e.headers or {}).get("x-server-time")
        hdrs = dict(e.headers or {})
    print("  HTTP %s  x-server-time=%s" % (st, srv))
    print("  body: %s" % sk_raw[:400])
    if st != 200:
        return
    j = json.loads(sk_raw)
    d = j.get("data") or j
    sign_key = d.get("signKey")
    epoch = d.get("epoch")
    print("  signKey=%s... epoch=%s expiresAt=%s"
          % (str(sign_key)[:16], epoch, d.get("expiresAt")))
    if not sign_key:
        return

    offset = 0.0
    if srv:
        try:
            v = float(srv)
            offset = (v if v > 1e12 else v * 1000) - (__import__("time").time() * 1000)
            print("  时钟偏移: %.0f ms" % offset)
        except Exception:
            pass

    print("\n== 3. 签名请求 /api/v1/usage ==")
    uid = (pc.get("userId") or cred.get("userId") or "3113399232")
    url = PLATFORM + "/api/v1/usage?userId=" + uid
    st, body, _ = signed_get(opener, url, epoch=epoch, sign_key=sign_key,
                              offset=offset)
    print("  HTTP %s" % st)
    print("  body: %s" % body[:800])


if __name__ == "__main__":
    main()
