import sys, re, os
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

M = r"C:\Users\yang2\AppData\Roaming\Xiaomi MiMo\runtime-res\releases\main\node~5knT2Qec.mjs"
t = open(M, encoding="utf-8", errors="replace").read()
SKILL = (17879189, 17885408)
def outside(i): return not (SKILL[0]-300 <= i <= SKILL[1]+300)

print("=== A) 更新器相关字符串 ===")
for pat in (r'latest[-\w]*\.yml', r'xiaomimimo\.com', r'mimocode-cdn', r'updateCheckNow', r'setFeedURL', r'channel'):
    hits = [m.start() for m in re.finditer(pat, t)]
    out = [i for i in hits if outside(i)]
    if out:
        print("\n  ### %s (%d hits, 技能区外 %d)" % (pat, len(hits), len(out)))
        for i in out[:6]:
            print("     @%d :: %s" % (i, t[max(0,i-350):i+350].replace("\n", " ")))

print("\n=== B) updater cache 目录 ===")
for d in (os.path.join(os.environ["LOCALAPPDATA"], "xiaomi-mimo-desktop-updater"),
          os.path.join(os.environ["LOCALAPPDATA"], "xiaomi-mimo-desktop-updater", "pending")):
    print(" ", d, "exists" if os.path.isdir(d) else "-")
    if os.path.isdir(d):
        for dp, dn, fns in os.walk(d):
            for f in fns:
                p = os.path.join(dp, f)
                print("    %-50s %10d" % (p.replace(d, ""), os.path.getsize(p)))

print("\n=== C) featureGatesSnapshot 的本地落地 ===")
for p in (r"C:\Users\yang2\AppData\Roaming\Xiaomi MiMo\feature-gates.json",):
    print(open(p, encoding="utf-8").read())
