import sys, re, os
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

P = r"C:\Users\yang2\AppData\Roaming\Xiaomi MiMo\runtime-res\releases\main\node~5knT2Qec.mjs"
t = open(P, encoding="utf-8").read()
SKILL = (17879189, 17885408)

def outside(i):
    return not (SKILL[0] - 200 <= i <= SKILL[1] + 200)

def show(pat, limit=25, ctx=500, label=None):
    print("=" * 110)
    print("### PATTERN:", label or pat)
    n = 0
    for m in re.finditer(re.escape(pat), t):
        i = m.start()
        if not outside(i):
            continue
        n += 1
        if n > limit:
            print("   ... more")
            break
        print("\n----- @%d -----\n%s" % (i, t[max(0, i - ctx):i + ctx]))
    print("  (total outside skill:", n, ")")

show("spritesheet", ctx=700)
show("animations", limit=20, ctx=450)
