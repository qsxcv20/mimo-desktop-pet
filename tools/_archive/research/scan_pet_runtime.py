import sys, re, os, io
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = r"C:\Users\yang2\AppData\Roaming\Xiaomi MiMo\runtime-res\releases"
OUT = r"D:\桌面宠物\_mimo"
os.makedirs(OUT, exist_ok=True)

PATS = [
    "spritesheet", "frameWidth", "totalFrames", "anchorX", "anchorY",
    "pets", "pet_", "mate", "desktop-companion", "companion",
    "leijun", "koala", "panda",
    "animations",
]

def scan(path, label, maxhits=6, ctx=420):
    try:
        raw = open(path, "rb").read()
    except Exception as e:
        print("!!", label, e); return
    for enc in ("utf-8", "utf-16"):
        try:
            t = raw.decode(enc); break
        except Exception:
            t = None
    if t is None:
        print("!! cannot decode", label); return
    print("=" * 100)
    print("FILE", label, "len", len(t))
    hits = {}
    for p in PATS:
        idxs = [m.start() for m in re.finditer(re.escape(p), t)]
        if idxs:
            hits[p] = idxs
    for p, idxs in hits.items():
        print("  %-18s %d hits" % (p, len(idxs)))
    return t, hits

# 1) main bundle
main_path = os.path.join(BASE, "main", "node~5knT2Qec.mjs")
t, hits = scan(main_path, "main/node~5knT2Qec.mjs")

lines = []
for p, idxs in hits.items():
    lines.append("\n\n########## PATTERN: %s  (%d hits) ##########" % (p, len(idxs)))
    for i in idxs[:40]:
        s = max(0, i - 300); e = min(len(t), i + 400)
        lines.append("\n----- @%d -----\n%s" % (i, t[s:e]))
open(os.path.join(OUT, "main-pet-context.txt"), "w", encoding="utf-8").write("\n".join(lines))
print("wrote main-pet-context.txt")

# 2) list renderer release dir
for sub in ("renderer", "preload"):
    d = os.path.join(BASE, sub)
    print("\n--- listing", d)
    try:
        for f in sorted(os.listdir(d)):
            p = os.path.join(d, f)
            print("   ", f, "(dir)" if os.path.isdir(p) else os.path.getsize(p))
    except Exception as e:
        print("   !!", e)
