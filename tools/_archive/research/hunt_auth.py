import sys, re, os, json
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

T = r"C:\Users\yang2\AppData\Roaming\Xiaomi MiMo\runtime-res\releases\main\main~DAq2tHkd.mjs"
t = open(T, encoding="utf-8", errors="replace").read()

print("=== 区域 -> base URL 映射 (om / Il) ===")
for pat in (r'om\s*=\s*\{', r'function Il\(', r'function sm\('):
    for m in re.finditer(pat, t):
        i = m.start()
        print("--- %s @%d ---" % (pat, i))
        print(t[i:i+700].replace("\n", " "))
        print()
        break

print("\n=== 桌面端 auth.json 原文 ===")
for p in (os.path.join(os.path.expanduser("~"), ".local", "share", "mimocode", "auth.json"),):
    print(p)
    print("   ", open(p, encoding="utf-8").read()[:400])

print("\n=== Local Storage 里找 xiaomi 登录凭据 ===")
ls = os.path.join(os.environ["APPDATA"], "Xiaomi MiMo", "Local Storage", "leveldb")
if os.path.isdir(ls):
    for fn in sorted(os.listdir(ls)):
        fp = os.path.join(ls, fn)
        if not os.path.isfile(fp) or os.path.getsize(fp) > 40 * 1024 * 1024:
            continue
        data = open(fp, "rb").read()
        for kw in (b"xiaomi", b"accessToken", b"access_token", b"mimo-token", b"platform.xiaomimimo"):
            if kw in data:
                i = data.find(kw)
                print("  %-22s %-18s @%d :: %s"
                      % (fn[:22], kw.decode(), i,
                         data[max(0, i - 120):i + 220].decode("utf-8", "replace").replace("\n", " ")))
                break
else:
    print("  (无 Local Storage leveldb)")

print("\n=== Windows 凭据 / 其它可能的 token 落点 ===")
for p in (os.path.join(os.environ["APPDATA"], "Xiaomi MiMo", "Local Storage", "leveldb"),
          os.path.join(os.environ["APPDATA"], "Xiaomi MiMo", "mimocode", "llm-server",
                       "fdd2f04f8f043115bdecb6f9863a0a7c0b5c67ff", "tokens.json")):
    if os.path.isfile(p):
        print(" ", p)
        print("   ", open(p, encoding="utf-8", errors="replace").read()[:600])
