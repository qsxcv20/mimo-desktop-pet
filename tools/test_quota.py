#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
test_quota.py — MiMo 额度/订阅 自测脚本。

用法：
    python D:\桌面宠物\tools\test_quota.py            # 人看的输出
    python D:\桌面宠物\tools\test_quota.py --json     # 附带原始 JSON
    python D:\桌面宠物\tools\test_quota.py --userdata "C:\...\Xiaomi MiMo"

退出码：0 = 跑完了（无论成功失败）；--strict 时失败返回 1。
"""

import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass  # pythonw.exe 下 sys.stdout 是 None
try:
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass  # pythonw.exe 下 sys.stderr 是 None

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pet"))

try:
    from mimo_quota import QuotaClient, MimoQuotaError, mask_secret
except Exception as e:  # pragma: no cover
    print("导入 pet/mimo_quota.py 失败：%s" % e)
    raise SystemExit(2)


def _rule(title):
    print("\n" + "=" * 62)
    print(title)
    print("=" * 62)


def _show_credentials(client):
    print("[1/4] 凭据（credentials）")
    creds = client.credentials()
    print("  userData  : %s" % client.userdata)
    print("  base URL  : %s" % client._api_bases()[0])
    print("  来源      : %s" % creds.get("source"))
    domains = creds.get("domains") or []
    print("  命中域名  : %s" % (", ".join(domains) if domains else "（无）"))
    cookies = creds.get("cookies") or {}
    if cookies:
        print("  cookie 数 : %d" % len(cookies))
        for name, value in cookies.items():
            print("     - %-24s = %s" % (name, mask_secret(value)))
    else:
        print("  cookie 数 : 0")
    if creds.get("error"):
        print("  ⚠ 错误    : %s" % creds["error"])
    return creds


def _show_usage(usage):
    print("\n[2/4] 额度（usage）")
    print("  URL       : %s" % usage.get("url"))
    print("  HTTP      : %s" % usage.get("status"))
    if usage.get("ok"):
        print("  percent   : %s" % usage.get("percent"))
        print("  resetDate : %s" % usage.get("resetDate"))
        print("  raw       : %s" % json.dumps(usage.get("raw"), ensure_ascii=False)[:400])
    else:
        print("  ✗ 失败    : %s" % usage.get("error"))


def _show_subscription(sub):
    print("\n[3/4] 订阅（subscription）")
    print("  URL       : %s" % sub.get("url"))
    print("  HTTP      : %s" % sub.get("status"))
    if sub.get("ok"):
        cur = sub.get("current") or {}
        print("  当前套餐  : %s" % (cur.get("title") or "（无）"))
        print("  planCode  : %s   planTier=%s   status=%s"
              % (cur.get("planCode"), cur.get("planTier"), cur.get("status")))
        print("  有效期    : %s ~ %s" % (cur.get("startTime"), cur.get("endTime")))
        print("  下次重置  : %s" % cur.get("nextResetTime"))
        subs = sub.get("subscriptions") or []
        print("  订阅条目  : %d" % len(subs))
        for s in subs:
            print("     - %s | %s | %s" % (s.get("title"), s.get("planCode"), s.get("status")))
    else:
        print("  ✗ 失败    : %s" % sub.get("error"))


def _show_snapshot(snap):
    print("\n[4/4] 快照（snapshot）")
    print("  抓取时间  : %s" % snap.get("fetchedAt"))
    print("  认证方式  : %s" % snap.get("auth"))
    print("  cookie源  : %s" % snap.get("cookieSource"))
    print("  ok        : %s" % snap.get("ok"))
    print("  percent   : %s" % snap.get("percent"))
    print("  resetDate : %s" % snap.get("resetDate"))
    cur = snap.get("current") or {}
    print("  当前套餐  : %s" % (cur.get("title") or "（无）"))


def main(argv):
    userdata = None
    as_json = False
    strict = False
    i = 1
    while i < len(argv):
        arg = argv[i]
        if arg == "--json":
            as_json = True
        elif arg == "--strict":
            strict = True
        elif arg == "--userdata" and i + 1 < len(argv):
            i += 1
            userdata = argv[i]
        else:
            print("未知参数：%s" % arg)
        i += 1

    _rule("MiMo 额度自测（%s）" % __import__("time").strftime("%Y-%m-%d %H:%M:%S"))

    client = QuotaClient(userdata=userdata)

    creds = _show_credentials(client)
    usage = client.usage()
    _show_usage(usage)
    sub = client.subscription()
    _show_subscription(sub)
    snap = client.snapshot()
    _show_snapshot(snap)

    print("\n" + "-" * 62)
    if usage.get("ok") and sub.get("ok"):
        print("结论：✅ 成功拿到额度 —— percent=%s，套餐=%s"
              % (usage.get("percent"), (snap.get("current") or {}).get("title")))
    else:
        failed = "凭据" if not creds.get("cookies") else ("额度" if not usage.get("ok") else "订阅")
        reason = creds.get("error") or usage.get("error") or sub.get("error")
        print("结论：❌ 失败，卡在「%s」这一步" % failed)
        print("      原因：%s" % reason)
        print("      建议：先完全退出 MiMo Desktop（托盘也退出），再重跑本脚本；")
        print("            Chromium cookie 库在运行期间被独占锁定，读不出来。")
    print("-" * 62)

    if as_json:
        print("\n--- 原始 JSON ---")
        print(json.dumps(
            {"credentials": creds, "usage": usage, "subscription": sub, "snapshot": snap},
            ensure_ascii=False, indent=2, default=str))

    ok = bool(usage.get("ok") and sub.get("ok"))
    return 0 if (ok or not strict) else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv))
    except SystemExit:
        raise
    except Exception as e:  # 兜底：不给堆栈
        print("\n脚本异常终止：%s: %s" % (type(e).__name__, e))
        raise SystemExit(2)
