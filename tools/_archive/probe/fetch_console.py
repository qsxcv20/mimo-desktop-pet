#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""fetch_console.py — 抓开放平台网页的 JS，找签名请求头的算法。

用法: python fetch_console.py
"""
import os
import re
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUT = r"D:\桌面宠物\_mimo\console"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")

os.makedirs(OUT, exist_ok=True)


def get(url, binary=False):
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = r.read()
    return data if binary else data.decode("utf-8", "replace")


def main():
    html = get("https://platform.xiaomimimo.com/")
    with open(os.path.join(OUT, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print("index.html %d bytes" % len(html))

    srcs = re.findall(r'<script[^>]+src="([^"]+)"', html)
    links = re.findall(r'<link[^>]+href="([^"]+\.js[^"]*)"', html)
    print("script src:", srcs)
    print("link js:", links)

    from urllib.parse import urljoin
    urls = [urljoin("https://platform.xiaomimimo.com/", s) for s in srcs + links]
    for u in urls:
        name = u.rsplit("/", 1)[-1].split("?")[0] or "index.js"
        try:
            data = get(u)
        except Exception as e:
            print("  fail", u, e)
            continue
        p = os.path.join(OUT, name)
        with open(p, "w", encoding="utf-8") as f:
            f.write(data)
        print("  saved %-40s %d bytes  %s" % (name, len(data), u))

        # 在里面找签名相关
        for kw in ("SIGN_MISSING", "/api/v1/usage", "tokenPlan/usage",
                   "X-Mimo-Sign", "signHeader", "signature"):
            if kw in data:
                i = data.find(kw)
                print("    ★ 命中 %s @%d" % (kw, i))
                print("      ..." + data[max(0, i - 400):i + 400].replace("\n", " ") + "...")


if __name__ == "__main__":
    main()
