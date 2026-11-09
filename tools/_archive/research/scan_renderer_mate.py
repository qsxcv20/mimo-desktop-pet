import sys, re, os
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RA = r"C:\Users\yang2\AppData\Roaming\Xiaomi MiMo\runtime-res\releases\renderer\assets"

PATS = [
    r'桌面伙伴', r'桌宠', r'Mate\b', r'\bmate[A-Z]', r'spritesheet',
    r'frameWidth', r'anchorX', r'totalFrames',
    r'pets', r'petId', r'pet\.id', r'petList', r'refreshPets',
    r'koala', r'panda', r'leijun', r'are-you-ok',
    r'companion', r'avatar',
]

summary = {}
for fn in sorted(os.listdir(RA)):
    p = os.path.join(RA, fn)
    if not os.path.isfile(p):
        continue
    try:
        data = open(p, "rb").read()
    except Exception:
        continue
    if len(data) > 8 * 1024 * 1024:
        continue
    t = data.decode("utf-8", "replace")
    found = []
    for pat in PATS:
        n = len(re.findall(pat, t))
        if n:
            found.append((pat, n))
            summary.setdefault(pat, []).append((fn, n))
    if found:
        print("%-46s %s" % (fn, ", ".join("%s:%d" % f for f in found)))

print("\n=== 汇总 ===")
for pat, lst in sorted(summary.items(), key=lambda kv: -sum(n for _, n in kv[1])):
    print("%-18s %s" % (pat, lst[:6]))
