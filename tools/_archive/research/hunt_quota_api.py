import sys, re, os, json
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

T = r"C:\Users\yang2\AppData\Roaming\Xiaomi MiMo\runtime-res\releases\main\main~DAq2tHkd.mjs"
t = open(T, encoding="utf-8", errors="replace").read()

print("=== 端点常量 ===")
for m in re.finditer(r'(UserUsage|Subscription)\s*:\s*"([^"]+)"', t):
    print("  %-16s = %s" % (m.group(1), m.group(2)))

print("\n=== 形如 /path 的端点字面量（含 usage/subscription/plan/quota/balance） ===")
seen = set()
for m in re.finditer(r'"(/[A-Za-z0-9_/\-{}.]{3,60})"', t):
    s = m.group(1)
    if re.search(r'usage|subscription|plan|quota|balance|limit|billing', s, re.I) and s not in seen:
        seen.add(s)
        print("  ", s)

print("\n=== xn() 是什么（URL 拼装） ===")
for m in re.finditer(r'function xn\(', t):
    i = m.start()
    print(t[i:i+700].replace("\n", " "))
    break

print("\n=== auth.json 位置与内容 ===")
for p in [os.path.join(os.path.expanduser("~"), ".local", "share", "mimocode", "auth.json"),
          os.path.join(os.environ.get("LOCALAPPDATA", ""), "mimocode", "auth.json")]:
    print(" ", p, "->", "存在" if os.path.isfile(p) else "不存在")
    if os.path.isfile(p):
        try:
            d = json.load(open(p, encoding="utf-8"))
            for k, v in d.items():
                if isinstance(v, dict):
                    print("      %s: keys=%s" % (k, sorted(v.keys())))
                    for kk, vv in v.items():
                        if kk in ("key", "sk", "token"):
                            print("         %s = %s..." % (kk, str(vv)[:24]))
                        elif kk in ("url", "base_url", "uid", "name", "email", "user_id"):
                            print("         %s = %s" % (kk, vv))
                else:
                    print("      %s: %s" % (k, str(v)[:60]))
        except Exception as e:
            print("      解析失败:", e)
