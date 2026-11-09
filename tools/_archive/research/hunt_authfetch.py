import sys, os, re, json
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

T = r"C:\Users\yang2\AppData\Roaming\Xiaomi MiMo\runtime-res\releases\main\main~DAq2tHkd.mjs"
t = open(T, encoding="utf-8", errors="replace").read()

print("=== authFetch 定义 ===")
for m in re.finditer(r'authFetch', t):
    i = m.start()
    seg = t[max(0, i - 900):i + 900]
    if "fetch" in seg and ("Authorization" in seg or "headers" in seg or "cookie" in seg.lower()):
        print(seg.replace("\n", " "))
        print()
        break

print("\n=== 'xiaomi' 凭据 key 在 auth.json 里的用法 ===")
for m in re.finditer(r'\.xiaomi\b', t):
    i = m.start()
    print(t[max(0, i - 500):i + 500].replace("\n", " "))
    print()
    break

print("\n=== Chromium cookie 库 ===")
net = os.path.join(os.environ["APPDATA"], "Xiaomi MiMo", "Network")
for dp, dn, fns in os.walk(net):
    for fn in fns:
        p = os.path.join(dp, fn)
        print("  %-40s %10d" % (p.replace(net, "."), os.path.getsize(p)))

print("\n=== Local State 的 os_crypt ===")
ls_path = os.path.join(os.environ["APPDATA"], "Xiaomi MiMo", "Local State")
if os.path.isfile(ls_path):
    d = json.load(open(ls_path, encoding="utf-8"))
    oc = d.get("os_crypt")
    print("  os_crypt keys:", sorted(oc.keys()) if oc else None)
    if oc and "encrypted_key" in oc:
        print("  encrypted_key (前 40):", oc["encrypted_key"][:40])
