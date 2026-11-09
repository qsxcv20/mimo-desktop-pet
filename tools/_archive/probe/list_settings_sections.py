import sys, os, re
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RA = r"C:\Users\yang2\AppData\Roaming\Xiaomi MiMo\runtime-res\releases\renderer\assets"
p = os.path.join(RA, "index~OePpplEX.js")
t = open(p, encoding="utf-8", errors="replace").read()
print("bundle:", os.path.basename(p), len(t), "chars")

print("\n=== 1) 设置页 i18n: 所有 section 名 ===")
secs = sorted(set(re.findall(r'section:"([^"]+)"', t)))
print(secs)

print("\n=== 2) 英文 i18n 中的 settings 分类标题 (形如 xxxTitle:\"...\") ===")
titles = sorted(set(re.findall(r'\b([a-zA-Z]+)Title:"([^"]{2,40})"', t)))
sec_like = [x for x in titles if re.search(r'worktree|hook|storage|general|appearance|personali|model|mcp|plugin|account|lab|notif|theme|key|mate|pet|companion|avatar', x[0] + x[1], re.I)]
for k, v in sec_like:
    print("   %-28s %s" % (k, v))

print("\n=== 3) Personalization 相关上下文 ===")
for m in re.finditer(r'[Pp]ersonalization', t):
    print("   @%d :: %s" % (m.start(), t[max(0, m.start()-260):m.start()+320].replace("\n", " ")))
    print()

print("\n=== 4) 'desktop companion' / 'avatar' 附近的英文文案 ===")
for pat in (r'desktop companion', r'desktopCompanion', r'avatar or desktop', r'Avatar or desktop'):
    for m in re.finditer(pat, t):
        print("   %s @%d :: %s" % (pat, m.start(), t[max(0, m.start()-200):m.start()+300].replace("\n", " ")))
