#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""cdp_probe.py — 探查 MiMo 渲染层里的 window.mimo。

用法: python cdp_probe.py
"""
import json
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"D:\桌面宠物\pet")

from mimo_cdp import MiMoCDP

EXPRS = [
    "typeof window.mimo",
    "window.mimo ? Object.keys(window.mimo).slice(0,80) : null",
    "typeof window.mimo?.getUserUsage",
    ("(async()=>{try{return await window.mimo.getUserUsage()}"
     "catch(e){return {err:String(e)}}})()"),
    ("(async()=>{try{return await window.mimo.getUserSubscription()}"
     "catch(e){return {err:String(e)}}})()"),
    ("(async()=>{try{return await window.mimo.userAuthSnapshot()}"
     "catch(e){return {err:String(e)}}})()"),
]


def main():
    c = MiMoCDP()
    tgt = c.pick_target()
    print("target: %s" % (tgt or {}).get("title"))
    for e in EXPRS:
        try:
            v = c.evaluate(e)
        except Exception as ex:
            v = "EXC: %s" % ex
        print("\n>> %s\n   %s" % (e[:70], json.dumps(v, ensure_ascii=False)[:600]))


if __name__ == "__main__":
    main()
