import sys, os, re
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

UD = r"C:\Users\yang2\AppData\Roaming\Xiaomi MiMo"
KEYS = [b"spritesheet", b"frameWidth", b"totalFrames", b"anchorX", b"leijun",
        b"are-you-ok", b"koala", b"mate", b"Mate"]

targets = []
for sub in ("resources", "on-demand-assets", "logs", "Local Storage", "WebStorage",
            "WebStorage" , "Session Storage", "Partitions", "db", "engine-config", "mimocode"):
    d = os.path.join(UD, sub)
    if os.path.isdir(d):
        targets.append(d)

for root in targets:
    for dirpath, dirnames, filenames in os.walk(root):
        for fn in filenames:
            p = os.path.join(dirpath, fn)
            try:
                sz = os.path.getsize(p)
            except Exception:
                continue
            if sz > 60 * 1024 * 1024:
                continue
            try:
                data = open(p, "rb").read()
            except Exception:
                continue
            found = [(k.decode(), data.count(k)) for k in KEYS if k in data]
            if found:
                print("%-78s %9d %s" % (p.replace(UD, "~"), sz, found))

print("\n=== resources tree ===")
R = os.path.join(UD, "resources")
for dirpath, dirnames, filenames in os.walk(R):
    depth = dirpath[len(R):].count(os.sep)
    if depth > 3:
        dirnames[:] = []
        continue
    for fn in filenames:
        p = os.path.join(dirpath, fn)
        print("  %-66s %9d" % (p.replace(R, "."), os.path.getsize(p)))
