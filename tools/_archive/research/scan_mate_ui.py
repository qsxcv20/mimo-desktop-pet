import sys, os, re
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

UD = r"C:\Users\yang2\AppData\Roaming\Xiaomi MiMo"
RA = os.path.join(UD, "runtime-res", "releases", "renderer", "assets")

print("=== A) 渲染层 assets: Mate 面板文案/键名 ===")
UI_PATS = [r'桌面宠物', r'桌面伙伴', r'desktop pet', r'Desktop Pet', r'desktop companion',
           r'Desktop Companion', r'mateTitle', r'petTitle', r'petManager', r'customPet',
           r'petSheet', r'spriteSheet', r'SpriteSheet', r'character pet', r'\bMATE\b']
for fn in sorted(os.listdir(RA)):
    p = os.path.join(RA, fn)
    if not os.path.isfile(p):
        continue
    data = open(p, "rb").read()
    if len(data) > 8 * 1024 * 1024:
        continue
    t = data.decode("utf-8", "replace")
    for pat in UI_PATS:
        for m in re.finditer(pat, t):
            print("  %-40s %-22s @%d :: %s" % (fn[:38], pat, m.start(),
                  t[max(0, m.start()-110):m.start()+160].replace("\n", " ")))

print("\n=== B) userData 全目录: spritesheet / leijun / pets 目录引用 ===")
KEYS = [b"spritesheet", b"leijun", b"are-you-ok"]
SKIP_DIRS = {"runtime-res", "runtimes", "db", "resources"}
for dirpath, dirnames, filenames in os.walk(UD):
    rel = os.path.relpath(dirpath, UD)
    top = rel.split(os.sep)[0]
    if top in SKIP_DIRS and rel != ".":
        dirnames[:] = []
        continue
    for fn in filenames:
        p = os.path.join(dirpath, fn)
        try:
            sz = os.path.getsize(p)
        except Exception:
            continue
        if sz > 40 * 1024 * 1024:
            continue
        try:
            data = open(p, "rb").read()
        except Exception:
            continue
        found = [(k.decode(), data.count(k)) for k in KEYS if k in data]
        if found:
            print("  %-70s %9d %s" % (p.replace(UD, "~"), sz, found))

print("\n=== C) leijun 预设的来源线索：文件时间戳 ===")
petd = os.path.join(UD, "pets", "leijun-are-you-ok")
for fn in sorted(os.listdir(petd)):
    fp = os.path.join(petd, fn)
    st = os.stat(fp)
    import datetime
    print("  %-20s %9d  mtime=%s" % (fn, st.st_size,
          datetime.datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S")))
exe = r"C:\Users\yang2\AppData\Local\Programs\Xiaomi MiMo\Xiaomi MiMo.exe"
import datetime
st = os.stat(exe)
print("  MiMo.exe 安装时间 mtime=%s" % datetime.datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S"))
