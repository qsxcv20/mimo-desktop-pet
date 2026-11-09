#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
preview_anim.py — 从 spritesheet.webp 按 manifest 逐帧回放，导出动画 GIF，
用来在装进 MiMo 之前肉眼验收每个动画状态。

用法:
    python preview_anim.py --pet D:\\桌面宠物\\build\\mimo-witch --out D:\\桌面宠物\\build\\_preview
    python preview_anim.py --pet <dir> --out <dir> --scale 2
"""

import argparse, json, os, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from PIL import Image

DECK = [(245, 245, 248), (228, 228, 234)]


def checker(w, h, cell=16):
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px = im.load()
    for y in range(h):
        for x in range(w):
            px[x, y] = DECK[((x // cell) + (y // cell)) % 2] + (255,)
    return im


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pet", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--scale", type=int, default=2)
    args = ap.parse_args()

    m = json.load(open(os.path.join(args.pet, "manifest.json"), encoding="utf-8"))
    sheet = Image.open(os.path.join(args.pet, m["spritesheet"])).convert("RGBA")
    F, C = m["frameWidth"], m["columns"]
    os.makedirs(args.out, exist_ok=True)

    print("精灵图 %dx%d, frame %d, cols %d" % (sheet.width, sheet.height, F, C))

    for name, a in sorted(m["animations"].items(), key=lambda kv: kv[1]["row"]):
        row, n = a["row"], a["frames"]
        # 回放规则：从 row 开始的第 0 帧起，按行优先(row-major)在网格中连续走 n 帧
        cells = []
        idx = 0
        for f in range(n):
            gi = idx
            r = row + gi // C
            c = gi % C
            if r * F >= sheet.height:
                print("  !! %s 第 %d 帧越界 (row %d)" % (name, f, r))
                break
            cells.append((c, r))
            idx += 1
        frames = []
        for (c, r) in cells:
            cell = sheet.crop((c * F, r * F, (c + 1) * F, (r + 1) * F))
            bg = checker(F, F)
            bg.alpha_composite(cell)
            frames.append(bg.convert("RGB").resize((F * args.scale, F * args.scale), Image.NEAREST))
        dur = int(1000 / max(1, a["fps"]))
        gif = os.path.join(args.out, "anim-%s.gif" % name)
        frames[0].save(gif, save_all=True, append_images=frames[1:], duration=dur, loop=0)
        print("  %-8s row=%d frames=%d fps=%d -> %s  (%.1f KB)"
              % (name, row, n, a["fps"], os.path.basename(gif),
                 os.path.getsize(gif) / 1024.0))

    # 拼一张 4 行静态对照图
    strips = []
    for name, a in sorted(m["animations"].items(), key=lambda kv: kv[1]["row"]):
        c = 0
        cell = sheet.crop((c * F, a["row"] * F, (c + 1) * F, (a["row"] + 1) * F))
        bg = checker(F, F)
        bg.alpha_composite(cell)
        strips.append(bg.convert("RGB"))
    W = F * len(strips)
    out = Image.new("RGB", (W, F), (255, 255, 255))
    for i, s in enumerate(strips):
        out.paste(s, (i * F, 0))
    p = os.path.join(args.out, "anim-strip.png")
    out.resize((W * args.scale // 2, F * args.scale // 2), Image.LANCZOS).save(p)
    print("静态对照:", p)


if __name__ == "__main__":
    main()
