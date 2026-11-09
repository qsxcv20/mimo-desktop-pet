import sys, re, os
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass  # pythonw.exe 下 sys.stdout 是 None

P = r"C:\Users\yang2\AppData\Roaming\Xiaomi MiMo\runtime-res\releases\main\node~5knT2Qec.mjs"
raw = open(P, "rb").read()
text = None
for enc in ("utf-8", "utf-16"):
    try:
        text = raw.decode(enc)
        print("decoded with", enc, "len", len(text))
        break
    except Exception as e:
        print("fail", enc, e)

TICK = chr(96)  # backtick

i = text.find("name: mate")
print("name:mate index =", i)

# find the SKILL.md template literal start
key = '"SKILL.md": ' + TICK
b = text.rfind(key, 0, i + 200)
print("SKILL.md literal start =", b)

# scan forward for the matching unescaped backtick
j = b + len(key)
end = None
while True:
    k = text.find(TICK, j)
    if k == -1:
        break
    # count preceding backslashes
    bs = 0
    p = k - 1
    while p >= 0 and text[p] == "\\":
        bs += 1
        p -= 1
    if bs % 2 == 0:
        end = k
        break
    j = k + 1

print("literal end =", end)
skill = text[b + len(key):end]
# unescape \` -> `
skill = skill.replace("\\`", "`").replace("\\$", "$").replace("\\\\", "\\")
out = r"D:\桌面宠物\_mimo\mate_skill_full.md"
os.makedirs(os.path.dirname(out), exist_ok=True)
open(out, "w", encoding="utf-8").write(skill)
print("skill chars =", len(skill))
print("--- tail 2500 ---")
print(skill[-2500:])
