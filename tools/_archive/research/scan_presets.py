import sys, os, re, json, struct
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

M = r"C:\Users\yang2\AppData\Roaming\Xiaomi MiMo\runtime-res\releases\main\node~5knT2Qec.mjs"
t = open(M, encoding="utf-8").read()

def ctx(pat, rad=1200, limit=6):
    out = []
    for m in re.finditer(re.escape(pat), t):
        out.append("\n----- @%d -----\n%s" % (m.start(), t[max(0, m.start()-rad):m.start()+rad]))
        if len(out) >= limit:
            break
    return "\n".join(out)

blob = []
for p in ("koala", "panda"):
    blob.append("########## %s ##########" % p)
    blob.append(ctx(p, 1500, 5))
open(r"D:\桌面宠物\_mimo\preset-context.txt", "w", encoding="utf-8").write("\n".join(blob))
print("wrote preset-context.txt")

# preset assets on disk?
print("\n=== main resources tree (depth 2, dirs) ===")
R = r"C:\Users\yang2\AppData\Roaming\Xiaomi MiMo\runtime-res\releases\main\resources"
for dirpath, dirnames, filenames in os.walk(R):
    depth = dirpath[len(R):].count(os.sep)
    if depth > 2:
        dirnames[:] = []
        continue
    for fn in filenames:
        p = os.path.join(dirpath, fn)
        try:
            sz = os.path.getsize(p)
        except Exception:
            sz = -1
        low = fn.lower()
        if low.endswith((".webp", ".png", ".gif")) or "pet" in low:
            print("  %-70s %10d" % (p.replace(R, "."), sz))
