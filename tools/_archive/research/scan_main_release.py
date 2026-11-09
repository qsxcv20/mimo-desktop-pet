import sys, os, re
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

M = r"C:\Users\yang2\AppData\Roaming\Xiaomi MiMo\runtime-res\releases\main"
KEYS = [b"pets", b"spritesheet", b"frameWidth", b"totalFrames", b"anchorX",
        b"leijun", b"koala", b"panda", b"manifest.json", b"alwaysOnTop",
        b"transparent", b"BrowserWindow", b"loadURL", b"idle", b"fps"]

files = []
for dp, dn, fns in os.walk(M):
    for fn in fns:
        if fn.endswith((".mjs", ".cjs", ".js")):
            files.append(os.path.join(dp, fn))

print("扫描 %d 个 JS 文件" % len(files))
hits = {}
for p in files:
    try:
        data = open(p, "rb").read()
    except Exception:
        continue
    if len(data) > 45 * 1024 * 1024:
        continue
    found = [(k.decode(), data.count(k)) for k in KEYS if k in data]
    if found:
        hits[p] = found

print("\n=== 含 pets/spritesheet/frameWidth/leijun/alwaysOnTop 的文件 ===")
for p, f in sorted(hits.items()):
    flag = [x for x in f if x[0] in ("pets", "spritesheet", "frameWidth", "totalFrames",
                                      "anchorX", "leijun", "alwaysOnTop")]
    mark = "  <<<" if flag else ""
    print("  %-62s %s%s" % (p.replace(M, "."), f, mark))

print("\n=== 重点文件上下文 ===")
TARGETS = [os.path.join(M, "canvas-client~B3m-nJE6.mjs"),
           os.path.join(M, "main~DAq2tHkd.mjs"),
           os.path.join(M, "ipc~Bb_5u4d9.mjs")]
for p in TARGETS:
    if not os.path.isfile(p):
        print(" MISS", p); continue
    t = open(p, encoding="utf-8", errors="replace").read()
    print("\n##### %s (%d bytes) #####" % (os.path.basename(p), len(t)))
    for pat in (b"pets", b"spritesheet", b"frameWidth", b"alwaysOnTop", b"transparent",
                b"BrowserWindow", b"loadURL", b"canvas"):
        for m in re.finditer(re.escape(pat), t):
            i = m.start()
            print("\n  --- %s @%d ---" % (pat.decode(), i))
            print("  " + t[max(0, i - 600):i + 800].replace("\n", " "))
            break
