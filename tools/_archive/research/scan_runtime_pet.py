import sys, os, re
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = r"C:\Users\yang2\AppData\Roaming\Xiaomi MiMo\runtime-res"
KEYS = [b"spritesheet", b"leijun", b"frameWidth", b"anchorX", b"totalFrames", b"koala"]

hits = []
for dirpath, dirnames, filenames in os.walk(ROOT):
    for fn in filenames:
        p = os.path.join(dirpath, fn)
        try:
            sz = os.path.getsize(p)
        except Exception:
            continue
        if sz > 120 * 1024 * 1024:
            continue
        try:
            with open(p, "rb") as f:
                data = f.read()
        except Exception:
            continue
        found = [k.decode() for k in KEYS if k in data]
        if found:
            hits.append((p, sz, found))
            print("%-70s %10d  %s" % (p.replace(ROOT, "~"), sz, found))

print("\n=== renderer release tree (non-assets) ===")
R = os.path.join(ROOT, "releases", "renderer")
for dirpath, dirnames, filenames in os.walk(R):
    if "assets" in dirpath and len(filenames) > 200:
        continue
    for fn in filenames:
        p = os.path.join(dirpath, fn)
        print("  %-60s %10d" % (p.replace(R, "."), os.path.getsize(p)))
