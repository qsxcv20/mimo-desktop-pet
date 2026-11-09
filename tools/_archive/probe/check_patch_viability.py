import sys, os, re, json
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

M = r"C:\Users\yang2\AppData\Roaming\Xiaomi MiMo\runtime-res\releases\main"

print("=== verify~C6iUpxXn.mjs (4KB) ===")
p = os.path.join(M, "verify~C6iUpxXn.mjs")
print(open(p, encoding="utf-8", errors="replace").read()[:3000])

print("\n=== runtime-res worker 里是否做逐文件哈希校验 ===")
for fn in ("lib-runtime-res-worker~-UkxIRy1.mjs",
           "lib-runtime-installation-worker~BhMgyjgc.mjs",
           "lib-runtime-res-startup-worker~CQ5blPFC.mjs"):
    fp = os.path.join(M, fn)
    if not os.path.isfile(fp):
        continue
    t = open(fp, encoding="utf-8", errors="replace").read()
    print("\n--- %s (%d bytes) ---" % (fn, len(t)))
    for pat in ("hash", "sha256", "verify", "digest", "integrity"):
        for m in re.finditer(pat, t, re.I):
            i = m.start()
            print("   %-9s @%d :: %s" % (pat, i, t[max(0, i-220):i+320].replace("\n", " ")))
            break

print("\n=== resource-index.json 的 hashes 结构（前 2 条） ===")
ri = json.load(open(r"C:\Users\yang2\AppData\Roaming\Xiaomi MiMo\runtime-res\resource-index.json",
                    encoding="utf-8"))
h = ri.get("hashes")
print("  hashes 类型:", type(h).__name__, "| 长度:", len(h) if h is not None else None)
if isinstance(h, dict):
    for k in list(h)[:2]:
        print("   ", k, "->", json.dumps(h[k])[:200])
elif isinstance(h, list):
    for k in h[:2]:
        print("   ", json.dumps(k)[:250])
print("  manifest 顶层键:", list(ri.keys()))
if "manifests" in ri:
    m0 = ri["manifests"]
    print("  manifests 类型:", type(m0).__name__, len(m0) if hasattr(m0, '__len__') else '')
