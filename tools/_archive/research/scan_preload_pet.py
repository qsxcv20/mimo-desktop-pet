import sys, re, os
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = r"C:\Users\yang2\AppData\Roaming\Xiaomi MiMo\runtime-res\releases"

FILES = [
    ("preload", os.path.join(BASE, "preload", "index~r-PVyE9U.js")),
    ("renderer/index", os.path.join(BASE, "renderer", "assets", "index~OePpplEX.js")),
    ("renderer/static", os.path.join(BASE, "renderer", "static", "index.html")),
]

PATS = [r'pet', r'mate', r'avatar', r'companion', r'sprite', r'frameWidth',
        r'refresh', r'Open Folder', r'openFolder', r'open_path', r'showItemInFolder']

for label, p in FILES:
    if not os.path.isfile(p):
        print("MISS", label, p); continue
    data = open(p, "rb").read()
    print("=" * 100)
    print("%s  (%s)  %d bytes" % (label, os.path.basename(p), len(data)))
    print("=" * 100)
    if p.endswith(".html"):
        t = data.decode("utf-8", "replace")
        print(t[:3000])
        continue
    t = data.decode("utf-8", "replace")
    hits = {}
    for pat in PATS:
        idxs = [m.start() for m in re.finditer(pat, t, re.I)]
        if idxs:
            hits[pat] = idxs
    for pat, idxs in hits.items():
        print("\n--- %s : %d hits ---" % (pat, len(idxs)))
        for i in idxs[:12]:
            print("   @%d  %s" % (i, t[max(0, i-160):i+220].replace("\n", " ")))
