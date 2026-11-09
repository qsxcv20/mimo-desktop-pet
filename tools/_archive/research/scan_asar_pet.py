import sys, re, os, json
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ASAR = r"C:\Users\yang2\AppData\Local\Programs\Xiaomi MiMo\resources\app.asar"
KEYS = [b"spritesheet", b"leijun", b"frameWidth", b"totalFrames", b"anchorX",
        b"pets/", b"petWindow", b"desktop-pet", b"pet.json", b"animations"]

size = os.path.getsize(ASAR)
print("asar size", size)

hits = {k: [] for k in KEYS}
CH = 8 * 1024 * 1024
off = 0
prev = b""
with open(ASAR, "rb") as f:
    while True:
        buf = f.read(CH)
        if not buf:
            break
        data = prev + buf
        base = off - len(prev)
        for k in KEYS:
            i = data.find(k)
            while i != -1:
                hits[k].append(base + i)
                i = data.find(k, i + 1)
        prev = data[-64:]
        off += len(buf)

for k in KEYS:
    print("%-14s %d" % (k.decode(), len(hits[k])))

# asar header: first 8 bytes pickle-ish; use node-like parse
with open(ASAR, "rb") as f:
    head = f.read(16)
print("head bytes", head[:16].hex())

# Dump contexts of spritesheet / leijun
out = []
for k in (b"spritesheet", b"leijun", b"frameWidth", b"anchorX"):
    for pos in hits[k][:12]:
        with open(ASAR, "rb") as f:
            f.seek(max(0, pos - 900))
            ctx = f.read(2200)
        try:
            s = ctx.decode("utf-8", errors="replace")
        except Exception:
            s = str(ctx)
        out.append("\n\n########## %s @ %d ##########\n%s" % (k.decode(), pos, s))
open(r"D:\桌面宠物\_mimo\asar-pet-ctx.txt", "w", encoding="utf-8").write("\n".join(out))
print("wrote asar-pet-ctx.txt")
