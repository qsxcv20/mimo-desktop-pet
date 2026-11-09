#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""fetch_chunks.py — 下载开放平台所有 chunk 并定位指定模块。

用法: python fetch_chunks.py [module_id ...]
"""
import os
import re
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUT = r"D:\桌面宠物\_mimo\console"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")
BASE = "https://platform.xiaomimimo.com/"


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read().decode("utf-8", "replace")


def main():
    os.makedirs(OUT, exist_ok=True)
    html = open(os.path.join(OUT, "index.html"), encoding="utf-8").read()

    # u.u = "static/" + (270===e?"main":e) + "." + {id:hash}
    m = re.search(r'u\.u=function\(e\)\{return"static/"\+\(270===e\?"main":e\)\+"\."\+\(\{(.*?)\}', html)
    if not m:
        print("没找到 chunk 映射")
        return
    pairs = re.findall(r'(\d+):"([0-9a-f]+)"', m.group(1))
    print("chunk 映射: %d 个" % len(pairs))

    files = []
    for cid, h in pairs:
        name = ("main" if cid == "270" else cid) + "." + h + ".chunk.js"
        url = BASE + "static/" + name
        path = os.path.join(OUT, name)
        if not os.path.isfile(path):
            try:
                data = get(url)
            except Exception as e:
                print("  fail %s %s" % (name, e))
                continue
            with open(path, "w", encoding="utf-8") as f:
                f.write(data)
        files.append((name, path))

    print("本地 chunk: %d 个" % len(files))

    mods = sys.argv[1:] or ["24705", "89041"]
    for mid in mods:
        pat = re.compile(r"(?<![0-9A-Za-z_$])" + re.escape(mid) + r":\s*(function|\(function)")
        hit = False
        for name, path in files:
            d = open(path, encoding="utf-8", errors="replace").read()
            mm = pat.search(d)
            if mm:
                i = mm.start()
                print("\n===== 模块 %s  在 %s @%d =====" % (mid, name, i))
                print(d[i:i + 1500].replace("\n", " "))
                hit = True
                break
        if not hit:
            print("\n模块 %s 没找到" % mid)


if __name__ == "__main__":
    main()
