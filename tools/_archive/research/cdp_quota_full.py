#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""cdp_quota_full.py — 打印 MiMo 侧额度/订阅/登录态的完整原始数据。"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pet"))

from mimo_cdp import MiMoCDP  # noqa: E402

CALLS = [
    ("userAuthSnapshot", "(async()=>{try{return await window.mimo.userAuthSnapshot()}"
                          "catch(e){return {err:String(e)}}})()"),
    ("getUserUsage", "(async()=>{try{return await window.mimo.getUserUsage()}"
                     "catch(e){return {err:String(e)}}})()"),
    ("getUserSubscription", "(async()=>{try{return await window.mimo.getUserSubscription()}"
                            "catch(e){return {err:String(e)}}})()"),
]

if __name__ == "__main__":
    c = MiMoCDP()
    if not c.available():
        print("调试端口不可用")
        raise SystemExit(1)
    for name, expr in CALLS:
        try:
            v = c.evaluate(expr, timeout=15)
        except Exception as e:
            v = {"err": str(e)}
        print("\n== %s ==" % name)
        print(json.dumps(v, ensure_ascii=False, indent=2)[:2500])
