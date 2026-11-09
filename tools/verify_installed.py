#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_installed.py — 直接从 MiMo userData/pets 下读取,做独立的字节级复核。
不复用构建目录的任何中间产物,确保"装进去的东西"本身是对的。
"""

import hashlib, json, os, sys
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass  # pythonw.exe 下 sys.stdout 是 None
from PIL import Image

UD = os.path.join(os.environ.get("APPDATA", ""), "Xiaomi MiMo")
PETS = os.path.join(UD, "pets")
TARGET = "mimo-witch"
D = os.path.join(PETS, TARGET)

fails = []
def chk(cond, msg):
    print(("  [OK]   " if cond else "  [FAIL] ") + msg)
    if not cond:
        fails.append(msg)

print("=" * 72)
print("安装目录:", D)
print("=" * 72)

chk(os.path.isdir(D), "目录存在")
if not os.path.isdir(D):
    sys.exit(1)

files = sorted(os.listdir(D))
print("\n-- 目录内容 --")
for f in files:
    p = os.path.join(D, f)
    print("   %-22s %9d bytes" % (f, os.path.getsize(p)))
chk(set(files) == {"manifest.json", "spritesheet.webp"},
    "目录只含契约必需的两个文件 (实际: %s)" % ", ".join(files))

mp = os.path.join(D, "manifest.json")
sp = os.path.join(D, "spritesheet.webp")

print("\n-- manifest.json --")
raw = open(mp, "rb").read()
chk(not raw.startswith(b"\xef\xbb\xbf"), "无 BOM (BOM 会让 JSON.parse 失败)")
m = json.loads(raw.decode("utf-8"))
print(json.dumps(m, ensure_ascii=False, indent=2))

for k in ("id", "name", "version", "spritesheet", "frameWidth",
          "frameHeight", "columns", "totalFrames", "animations"):
    chk(k in m, "含必需字段 %s" % k)
chk(m.get("id") == TARGET, "id 与目录名一致 (%s)" % m.get("id"))
chk(m.get("version") == 1, "version == 1")
chk(m.get("spritesheet") == "spritesheet.webp", "spritesheet 指向实际文件名")
chk("idle" in m.get("animations", {}), "含必需的 idle 动画")

print("\n-- spritesheet.webp --")
head = open(sp, "rb").read(16)
chk(head[:4] == b"RIFF" and head[8:12] == b"WEBP", "合法 WebP 头 (RIFF....WEBP)")
sz = os.path.getsize(sp)
chk(sz < 2 * 1024 * 1024, "体积 %.1f KB < 2MB" % (sz / 1024.0))

im = Image.open(sp)
im.load()
chk(im.format == "WEBP", "Pillow 识别格式为 WEBP (%s)" % im.format)
chk(im.mode == "RGBA", "模式 RGBA (%s)" % im.mode)
lo, hi = im.getchannel("A").getextrema()
chk(lo < 255, "含透明像素 (alpha %d..%d)" % (lo, hi))

fw, fh, cols = m["frameWidth"], m["frameHeight"], m["columns"]
rows = max(a["row"] for a in m["animations"].values()) + 1
chk(im.width == fw * cols, "宽 %d == frameWidth*columns %d" % (im.width, fw * cols))
chk(im.height == fh * rows, "高 %d == frameHeight*rows %d" % (im.height, fh * rows))
chk(m["totalFrames"] == fw * 0 + (im.width // fw) * (im.height // fh),
    "totalFrames %d == 网格单元数 %d" % (m["totalFrames"], (im.width // fw) * (im.height // fh)))

print("\n-- 每个动画的帧是否都落在精灵图内 --")
for name, a in sorted(m["animations"].items(), key=lambda kv: kv[1]["row"]):
    last = a["row"] * cols + a["frames"] - 1
    lr, lc = divmod(last, cols)
    inside = (lr < im.height // fh) and (lc < cols)
    nonempty = True
    for f in range(a["frames"]):
        gi = a["row"] * cols + f
        r, c = divmod(gi, cols)
        cell = im.crop((c * fw, r * fh, (c + 1) * fw, (r + 1) * fh))
        if cell.getchannel("A").getbbox() is None:
            nonempty = False
    chk(inside and nonempty,
        "%-6s row=%d frames=%d -> 占用到 row%d col%d, 全部帧有像素"
        % (name, a["row"], a["frames"], lr, lc))

print("\n-- 与官方预设对比(结构同构性) --")
REF = os.path.join(PETS, "leijun-are-you-ok")
if os.path.isdir(REF):
    rm = json.load(open(os.path.join(REF, "manifest.json"), encoding="utf-8"))
    rim = Image.open(os.path.join(REF, rm["spritesheet"]))
    print("   官方预设: frame %dx%d cols %d totalFrames %d  精灵图 %dx%d  %.0fKB"
          % (rm["frameWidth"], rm["frameHeight"], rm["columns"],
             rm["totalFrames"], rim.width, rim.height,
             os.path.getsize(os.path.join(REF, rm["spritesheet"])) / 1024))
    print("   本桌宠  : frame %dx%d cols %d totalFrames %d  精灵图 %dx%d  %.0fKB"
          % (fw, fh, cols, m["totalFrames"], im.width, im.height, sz / 1024))
    # frameWidth/frameHeight 由 manifest 自己声明（MiMo 随包的 skill 文档里
    # 写明这两个字段是「每帧的宽/高」，240 只是 *推荐值*，不是契约要求）。
    # 官方预设是 240，我们为了把 12 帧 x 4 行塞进 2MB 用了 192，
    # 只要 manifest 与精灵图尺寸自洽即可，所以这里只做提示、不判失败。
    print("   [INFO] 帧尺寸与官方预设不同（%dx%d vs %dx%d）："
          "契约允许，manifest 自声明即可"
          % (fw, fh, rm["frameWidth"], rm["frameHeight"]))
    chk(set(rm.keys()) <= set(m.keys()) | {"description", "anchorX"},
        "字段集与官方预设同构")

print("\n-- 与构建产物的哈希一致性 --")
# 注意：装进 pets 目录的是 **Mate 精简版**（build/mimo-witch-mate），
# 不是主精灵图（build/mimo-witch）。比错目录会一直报不一致。
src = os.environ.get("MIMO_PET_BUILD_DIR",
                     r"D:\桌面宠物\build\mimo-witch-mate")
if os.path.isdir(src):
    print("   构建目录:", src)
    for f in ("manifest.json", "spritesheet.webp"):
        a = hashlib.sha256(open(os.path.join(src, f), "rb").read()).hexdigest()
        b = hashlib.sha256(open(os.path.join(D, f), "rb").read()).hexdigest()
        chk(a == b, "%s sha256 与构建产物一致 (%s)" % (f, b[:16]))
else:
    print("   [跳过] 构建目录不存在:", src)

print("\n" + "=" * 72)
if fails:
    print("复核结果: %d 项未通过" % len(fails))
    for f in fails:
        print("   - " + f)
    sys.exit(1)
print("复核结果: 全部通过 —— 文件已完整落到 MiMo 的 pets 目录")
print("=" * 72)
