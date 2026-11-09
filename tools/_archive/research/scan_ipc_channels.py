import sys, re, os
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = r"C:\Users\yang2\AppData\Roaming\Xiaomi MiMo\runtime-res\releases"

print("=== A) preload 暴露的全部 mimo: IPC 通道名 ===")
pre = os.path.join(BASE, "preload", "index~r-PVyE9U.js")
t = open(pre, encoding="utf-8", errors="replace").read()
chans = sorted(set(re.findall(r'"mimo:([A-Za-z0-9_.]+)"', t)))
print("共 %d 个:" % len(chans))
petlike = [c for c in chans if re.search(r'pet|mate|avatar|companion|sprite|char', c, re.I)]
print("  含 pet/mate/avatar/companion/sprite 的通道:", petlike if petlike else "无")
for i in range(0, len(chans), 6):
    print("   ", ", ".join(chans[i:i+6]))

print("\n=== B) 主进程: 透明置顶窗口 (桌宠 overlay 窗口) ===")
M = os.path.join(BASE, "main", "node~5knT2Qec.mjs")
m = open(M, encoding="utf-8", errors="replace").read()
SKILL = (17879189, 17885408)
def outside(i): return not (SKILL[0]-300 <= i <= SKILL[1]+300)

for pat in (r'transparent:\s*!0', r'alwaysOnTop:\s*!0', r'transparent:\s*true', r'alwaysOnTop:\s*true'):
    hits = [x.start() for x in re.finditer(pat, m)]
    out = [i for i in hits if outside(i)]
    print("  %-24s 共 %d 命中, 技能区外 %d" % (pat, len(hits), len(out)))
    for i in out[:4]:
        print("      @%d :: %s" % (i, m[max(0,i-300):i+300].replace("\n"," ")))

print("\n=== C) 主进程里所有 BrowserWindow 的窗口名/标题 ===")
names = sorted(set(re.findall(r'new BrowserWindow\(\{[^}]{0,400}?title:\s*"([^"]+)"', m)))
print("  titles:", names[:40])
wins = sorted(set(re.findall(r'title:\s*"([^"]{2,40})"', m)))
print("  全部 title 字面量(前50):", wins[:50])
