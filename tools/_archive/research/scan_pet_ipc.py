import sys, re, os
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

M = r"C:\Users\yang2\AppData\Roaming\Xiaomi MiMo\runtime-res\releases\main\node~5knT2Qec.mjs"
t = open(M, encoding="utf-8").read()
SKILL = (17879189, 17885408)

def outside(i):
    return not (SKILL[0] - 300 <= i <= SKILL[1] + 300)

# 精确找作为字符串/路径字面量出现的 pets / manifest.json / pet 相关 IPC 通道
PATS = [
    r'"pets"', r"'pets'", r'/pets', r'pets/', r'`pets',
    r'"manifest\.json"', r"'manifest\.json'",
    r'pet:[a-zA-Z]', r'mate:[a-zA-Z]', r'"pet\.[a-zA-Z]+"', r'pet-[a-z]',
    r'readdirSync', r'frameWidth',
]

seen = set()
out = []
for p in PATS:
    for m in re.finditer(p, t):
        i = m.start()
        if not outside(i):
            continue
        key = (p, i // 400)
        if key in seen:
            continue
        seen.add(key)
        out.append((i, p, t[max(0, i - 900):i + 900]))

out.sort()
lines = []
for i, p, ctx in out:
    lines.append("\n\n########## %s @ %d ##########\n%s" % (p, i, ctx))
open(r"D:\桌面宠物\_mimo\pets-ipc-ctx.txt", "w", encoding="utf-8").write("".join(lines))
print("wrote pets-ipc-ctx.txt, blocks:", len(out))
for i, p, _ in out[:60]:
    print("  %-22s @ %d" % (p, i))
