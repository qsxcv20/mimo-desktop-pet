import sys, re, os, urllib.request, json
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RA = r"C:\Users\yang2\AppData\Roaming\Xiaomi MiMo\runtime-res\releases\renderer\assets"
present = sorted(os.listdir(RA))
print("=== 页面/功能类 chunk ===")
for f in present:
    if re.search(r'Page|Panel|Lab|Mate|Pet|Overlay|Window|Companion|Settings', f, re.I):
        print("   ", f, os.path.getsize(os.path.join(RA, f)))

print("\n=== Lab 页里的开关 (feature flags) ===")
lab = [f for f in present if re.match(r'Lab', f)]
for f in lab:
    t = open(os.path.join(RA, f), encoding="utf-8", errors="replace").read()
    print("--- %s (%d bytes) ---" % (f, len(t)))
    # 形如 {key:"...", label:"..."} 或 flag 名
    for m in re.finditer(r'([a-zA-Z][a-zA-Z0-9_]{3,28})\s*:\s*(?:\{[^}]{0,120}?label|"[^"]{2,40}"|!0|!1|true|false)', t):
        print("     ", m.group(0)[:110].replace("\n", " "))

print("\n=== 全渲染层搜 lab/mate 相关 flag 名 ===")
allflags = {}
for f in present:
    t = open(os.path.join(RA, f), encoding="utf-8", errors="replace").read()
    for m in re.finditer(r'(showMate|mateEnabled|enableMate|showPet|petEnabled|enablePet|desktopPet|desktopCompanion|showDesktopCompanion|showAvatar|mascot|tamagotchi)', t, re.I):
        allflags.setdefault(m.group(0).lower(), []).append((f, m.start()))
for k, v in allflags.items():
    print("   %-24s %s" % (k, v[:5]))
if not allflags:
    print("   (无)")

print("\n=== CDN: 找可用版本 ===")
BASE = "https://mimocode-cdn.xiaomimimo.com/mimocode/mimodesktop/"
paths = ["latest.yml", "latest-mac.yml", "win/latest.yml", "stable/latest.yml",
         "channel/stable/latest.yml", "XiaomiMiMo-26.1102.21158-x64-setup.exe",
         "latest.yml?v=1", ""]
for p in paths:
    u = BASE + p
    try:
        req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            body = r.read(600)
            print("  %-46s -> %s  %s" % (p, r.status, body[:300]))
    except Exception as e:
        code = getattr(e, "code", "")
        print("  %-46s -> ERR %s %s" % (p, code, str(e)[:80]))
