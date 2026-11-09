#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""find_auth_xiaomi.py — 全盘找带 .xiaomi 凭据的 auth.json。"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOTS = [
    os.path.expanduser("~"),
    os.path.join(os.environ["APPDATA"], "Xiaomi MiMo"),
    os.path.join(os.environ["LOCALAPPDATA"], "Xiaomi MiMo"),
]
SKIP = {"node_modules", "AppData", ".git", "runtimes", "resources",
        "runtime-res", "engine-config", "site-packages", "Windows",
        "Program Files", "Program Files (x86)"}

found = []
for root in ROOTS:
    if not os.path.isdir(root):
        continue
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in SKIP]
        depth = dp[len(root):].count(os.sep)
        if depth > 6:
            dns[:] = []
        for fn in fns:
            if fn != "auth.json":
                continue
            p = os.path.join(dp, fn)
            try:
                data = json.load(open(p, "r", encoding="utf-8"))
            except Exception as e:
                print("  (skip %s: %s)" % (p, e))
                continue
            keys = list(data.keys()) if isinstance(data, dict) else []
            print("\n### %s" % p)
            print("    providers:", keys)
            if "xiaomi" in keys:
                x = data["xiaomi"]
                print("    !!! xiaomi 凭据:")
                print(json.dumps(x, ensure_ascii=False, indent=2)[:1200])
                found.append((p, x))

print("\n\n=== 汇总 ===")
for p, x in found:
    print("  %s -> base=%s uid=%s key=%s..." % (
        p, (x.get("metadata") or {}).get("base_url"),
        (x.get("metadata") or {}).get("uid") or (x.get("metadata") or {}).get("user_id"),
        (x.get("key") or "")[:12]))
if not found:
    print("  没找到 .xiaomi 凭据")
