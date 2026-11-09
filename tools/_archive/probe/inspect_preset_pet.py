import sys, os, json, re
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from PIL import Image

PETS = r"C:\Users\yang2\AppData\Roaming\Xiaomi MiMo\pets"
print("=== pets dir ===")
for dirpath, dirnames, filenames in os.walk(PETS):
    for fn in filenames:
        p = os.path.join(dirpath, fn)
        print("  %-60s %9d" % (p.replace(PETS, "~"), os.path.getsize(p)))

for pet in os.listdir(PETS):
    mf = os.path.join(PETS, pet, "manifest.json")
    if not os.path.isfile(mf):
        continue
    m = json.load(open(mf, encoding="utf-8"))
    print("\n### manifest", pet)
    print(json.dumps(m, ensure_ascii=False, indent=2))
    sp = os.path.join(PETS, pet, m.get("spritesheet", ""))
    if os.path.isfile(sp):
        im = Image.open(sp)
        print("  spritesheet:", im.size, im.mode, "format", im.format)
        fw, fh = m.get("frameWidth", 0), m.get("frameHeight", 0)
        cols, tf = m.get("columns", 0), m.get("totalFrames", 0)
        print("  grid: %dx%d cols=%d total=%d -> implied cells %d" % (fw, fh, cols, tf, fw*cols*fh*cols))
        print("  implied total width/height: %d x %d" % (fw*cols, fh*max(1, tf//cols if cols else 1)))

print("\n=== renderer assets: search 'pets' / 'manifest.json' ===")
RA = r"C:\Users\yang2\AppData\Roaming\Xiaomi MiMo\runtime-res\releases\renderer\assets"
KEYS = [b"pets", b"manifest.json", b"userData", b"leijun", b"are-you-ok", b"\xe6\xa1\x8c\xe5\x8f\xa0\xe4\xbc\x99\xe4\xbc\xb4"]
for fn in sorted(os.listdir(RA)):
    p = os.path.join(RA, fn)
    if not os.path.isfile(p):
        continue
    data = open(p, "rb").read()
    found = []
    for k in KEYS:
        n = data.count(k)
        if n:
            found.append((k.decode("utf-8", "replace"), n))
    if found:
        print("  %-46s %s" % (fn, found))
