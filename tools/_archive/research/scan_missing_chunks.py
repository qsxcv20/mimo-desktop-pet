import sys, re, os
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RA = r"C:\Users\yang2\AppData\Roaming\Xiaomi MiMo\runtime-res\releases\renderer\assets"
present = set(os.listdir(RA))

print("=== A) index bundle 里引用但本地缺失的 chunk ===")
t = open(os.path.join(RA, "index~OePpplEX.js"), encoding="utf-8", errors="replace").read()
refs = sorted(set(re.findall(r'"\./([A-Za-z0-9_\-~]+\.(?:js|css))"', t)))
missing = [r for r in refs if r not in present]
print("  引用总数 %d, 本地缺失 %d" % (len(refs), len(missing)))
for r in missing:
    print("    MISSING:", r)

print("\n=== B) __vite__mapDeps 条目 ===")
m = re.search(r'__vite__mapDeps\s*=\s*\(i,\s*l\)\s*=>\s*\(\{\s*\.map\(.*?\}\)\[i\]', t)
dep = re.findall(r'"([A-Za-z0-9_\-~]+\.(?:js|css))"', t[:400000])
dmiss = sorted(set(d for d in dep if d not in present))
print("  早期依赖引用 %d, 缺失 %d" % (len(set(dep)), len(dmiss)))
for r in dmiss[:20]:
    print("    MISSING:", r)

print("\n=== C) 有没有远程 import / fetch CDN ===")
for pat in (r'https://[^"\'`\s]{10,120}', r'fetch\(', r'new URL\('):
    hits = [m.start() for m in re.finditer(pat, t)]
    urls = set()
    for i in hits[:400]:
        mm = re.match(r'https://[^"\'`\s]{10,120}', t[i:i+160])
        if mm:
            urls.add(mm.group(0))
    if urls:
        print("  %-12s -> %s" % (pat, list(urls)[:8]))

print("\n=== D) update-info.json ===")
p = r"C:\Users\yang2\AppData\Local\xiaomi-mimo-desktop-updater\pending\update-info.json"
print(open(p, encoding="utf-8").read())
