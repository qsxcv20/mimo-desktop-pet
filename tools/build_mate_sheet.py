#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""build_mate_sheet.py — 从主精灵图派生一份「Mate 精简版」。

MiMo Mate 契约要求 spritesheet.webp < 2MB。主精灵图（256px × 24 帧 × 4 行）
无损 webp 有 6.3MB，装不进 Mate。

这里做两件事：
  1. 每行等间隔抽 12 帧（24 -> 12），帧率不变，动画节奏基本保留
  2. 帧尺寸降到 192px，并用有损 webp（透明通道仍然保留）

产物写到 build/mimo-witch-mate/，用 install_mate_pet.py 装到 MiMo 的 pets 目录。

用法:
    python build_mate_sheet.py
    python build_mate_sheet.py --cols 12 --frame 192 --quality 88
"""
import argparse
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass  # pythonw.exe 下 sys.stdout 是 None
from PIL import Image

ROOT = r"D:\桌面宠物"
SRC = os.path.join(ROOT, "build", "mimo-witch")
OUT = os.path.join(ROOT, "build", "mimo-witch-mate")
EXPRESSIONS = ["idle", "happy", "think", "tired"]
LIMIT = 2 * 1024 * 1024


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=SRC)
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--cols", type=int, default=12)
    ap.add_argument("--frame", type=int, default=192)
    ap.add_argument("--quality", type=int, default=88)
    ap.add_argument("--pet-id", default="mimo-witch")
    ap.add_argument("--name", default="MiMo 巫女兔")
    ap.add_argument("--desc", default="橙白双马尾女巫帽兔耳少女 · MiMo 桌面伙伴")
    args = ap.parse_args()

    mp = os.path.join(args.src, "manifest.json")
    manifest = json.load(open(mp, encoding="utf-8"))
    sheet = Image.open(os.path.join(args.src, manifest["spritesheet"])).convert("RGBA")
    sw, sh = sheet.size
    src_cols = manifest["columns"]
    src_frame = manifest["frameWidth"]
    rows = len(EXPRESSIONS)

    print("源: %dx%d  frame=%d cols=%d" % (sw, sh, src_frame, src_cols))

    # 抽帧索引：等间隔。
    # 但**眨眼帧必须保留** —— 主精灵图 24 帧里只有 3 帧是眨眼，
    # 等间隔抽 12 帧会把「闭得最狠」那帧抽掉，Mate 里的眨眼就只剩半睁。
    # 所以每个表情都先把它的眨眼帧锁死，剩下的名额再等间隔补。
    BLINK = {"idle": (13, 14, 15), "think": (16, 17, 18), "tired": (8, 9, 10),
             "happy": ()}

    def pick_idx(expr):
        need = args.cols
        keep = sorted(set(BLINK.get(expr, ())) & set(range(src_cols)))
        rest = [i for i in range(src_cols) if i not in keep]
        n = need - len(keep)
        sel = []
        if n > 0 and rest:
            if n == 1:
                sel = [rest[len(rest) // 2]]
            else:
                sel = sorted(set(rest[round(i * (len(rest) - 1) / float(n - 1))]
                                 for i in range(n)))
        idx = sorted(set(keep) | set(sel))
        # 不够就用等间隔补齐
        for i in range(src_cols):
            if len(idx) >= need:
                break
            if i not in idx:
                idx = sorted(idx + [i])
        return idx[:need]

    f = args.frame
    out_sheet = Image.new("RGBA", (f * args.cols, f * rows), (0, 0, 0, 0))
    for r in range(rows):
        expr = EXPRESSIONS[r] if r < len(EXPRESSIONS) else ""
        idx = pick_idx(expr)
        print("  %-6s 抽帧 %s" % (expr, idx))
        for k, si in enumerate(idx):
            fr = sheet.crop((si * src_frame, r * src_frame,
                             (si + 1) * src_frame, (r + 1) * src_frame))
            fr = fr.resize((f, f), Image.LANCZOS)
            out_sheet.alpha_composite(fr, (k * f, r * f))

    os.makedirs(args.out, exist_ok=True)
    png = os.path.join(args.out, "spritesheet.png")
    out_sheet.save(png)
    webp = os.path.join(args.out, "spritesheet.webp")
    out_sheet.save(webp, "WEBP", quality=args.quality, method=6)
    size = os.path.getsize(webp)
    print("Mate 精灵图 %dx%d  webp %.1f KB"
          % (out_sheet.width, out_sheet.height, size / 1024.0))

    if size > LIMIT:
        print("!! 仍然超过 2MB，再降一档质量试试：--quality %d"
              % max(60, args.quality - 10))

    # fps 保持不变（抽帧后循环更快，视觉上更利落）
    m = dict(manifest)
    m["spritesheet"] = "spritesheet.webp"
    m["frameWidth"] = f
    m["frameHeight"] = f
    m["columns"] = args.cols
    m["totalFrames"] = args.cols * rows
    m["id"] = args.pet_id
    m["name"] = args.name
    m["description"] = args.desc
    m["version"] = 1
    anims = {}
    for r, expr in enumerate(EXPRESSIONS):
        a = dict(manifest["animations"].get(expr, {}))
        a["row"] = r
        a["frames"] = args.cols
        anims[expr] = a
    m["animations"] = anims

    mp2 = os.path.join(args.out, "manifest.json")
    with open(mp2, "w", encoding="utf-8") as fh:
        json.dump(m, fh, ensure_ascii=False, indent=2)
    print("manifest ->", mp2)
    print("\n下一步：")
    print('  python "%s\\tools\\install_mate_pet.py" --src "%s"'
          % (ROOT, args.out))


if __name__ == "__main__":
    main()
