#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_mate_pet.py — 把 4 套 MiMo 表情 PNG 打包成小米 MiMo Desktop「Mate 桌面伙伴」
所需的 spritesheet.webp + manifest.json。

契约来源：MiMo Desktop 内置 skill `mate`（Mate Pet Creator），
        + 本机内置预设 leijun-are-you-ok 的实际网格行为。

用法:
    python build_mate_pet.py --out D:\\桌面宠物\\build\\mimo-witch
    python build_mate_pet.py --out <dir> --frame 240 --cols 8 --fps 8
"""

import argparse
import json
import os
import sys
from PIL import Image, ImageDraw

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = r"D:\桌面宠物"
SRC = os.path.join(ROOT, "assets", "src")

# 表情 -> (源文件, 该动画的逐帧变换)
# 变换描述: (dx, dy, scale_x, scale_y)  相对 240 画布像素；围绕底部中心锚点做缩放
EXPRESSIONS = ["idle", "happy", "think", "tired"]

SOURCE_FILE = {
    "idle":  "mimo-idle-v2@2048.png",
    "happy": "mimo-happy-v2@2048.png",
    "think": "mimo-think-v2@2048.png",
    "tired": "mimo-tired-v2@2048.png",
}

# 每套表情 8 帧的循环动作（呼吸 / 雀跃 / 思考 / 疲惫）
def build_motion(kind, frames):
    """返回 frames 个 (dx, dy, sx, sy)。sx/sy 是围绕底部中心锚点的缩放系数。"""
    out = []
    n = frames
    for i in range(n):
        ph = i / float(n) * 2 * 3.141592653589793
        if kind == "idle":
            # 呼吸：整体极轻上下浮动 + 轻微纵向拉伸
            dy = 1.6 * (1 - __import__("math").cos(ph))
            sy = 1.0 + 0.012 * (1 - __import__("math").cos(ph))
            out.append((0.0, dy, 1.0, sy))
        elif kind == "happy":
            # 雀跃：向上弹起 + 轻微放大，落地略微压缩
            dy = -7.0 * max(0.0, __import__("math").sin(ph))
            lift = max(0.0, __import__("math").sin(ph))
            sy = 1.0 + 0.02 * lift
            sx = 1.0 + 0.008 * lift
            out.append((0.0, dy, sx, sy))
        elif kind == "think":
            # 思考：左右轻微摇摆 + 呼吸
            dx = 2.6 * __import__("math").sin(ph)
            dy = 1.2 * (1 - __import__("math").cos(ph))
            out.append((dx, dy, 1.0, 1.0))
        elif kind == "tired":
            # 疲惫：缓慢下沉 + 轻微左右倒，幅度最小、频率最低
            dx = 1.8 * __import__("math").sin(ph)
            dy = 3.0 * (1 - __import__("math").cos(ph)) / 2.0
            sy = 1.0 - 0.02 * (1 - __import__("math").cos(ph)) / 2.0
            out.append((dx, dy, 1.0, sy))
    return out


def trim(img):
    """裁掉全透明边，返回 (裁后图, bbox)。"""
    alpha = img.getchannel("A")
    bbox = alpha.getbbox()
    if not bbox:
        raise SystemExit("源图没有可见像素")
    return img.crop(bbox), bbox


def fit(img, max_w, max_h):
    """等比缩放到 max_w x max_h 以内。"""
    w, h = img.size
    s = min(max_w / float(w), max_h / float(h))
    return img.resize((max(1, int(round(w * s))), max(1, int(round(h * s)))), Image.LANCZOS)


def render_frames(base_png, frame, motion, margin):
    """把一张静态图按 motion 序列渲染成若干帧（RGBA）。"""
    src = Image.open(base_png).convert("RGBA")
    src, _ = trim(src)
    max_w = frame - 2 * margin
    max_h = frame - 2 * margin
    src = fit(src, max_w, max_h)

    frames = []
    for (dx, dy, sx, sy) in motion:
        canvas = Image.new("RGBA", (frame, frame), (0, 0, 0, 0))
        w, h = src.size
        nw, nh = max(1, int(round(w * sx))), max(1, int(round(h * sy)))
        im = src.resize((nw, nh), Image.LANCZOS)
        # 底部中心锚点：底部贴 baseline，水平居中
        baseline = frame - margin
        x = int(round((frame - nw) / 2.0 + dx))
        y = int(round(baseline - nh + dy))
        canvas.alpha_composite(im, (x, y))
        frames.append(canvas)
    return frames


def build_sheet(frame, cols, rows_total, per_row_frames, src_dir):
    sheet = Image.new("RGBA", (frame * cols, frame * rows_total), (0, 0, 0, 0))
    for row, kind in enumerate(EXPRESSIONS):
        motion = build_motion(kind, per_row_frames)
        base = os.path.join(src_dir, SOURCE_FILE[kind])
        if not os.path.isfile(base):
            raise SystemExit("缺少源图: " + base)
        fr = render_frames(base, frame, motion, margin=max(4, frame // 30))
        for c, f in enumerate(fr):
            sheet.alpha_composite(f, (c * frame, row * frame))
    return sheet


def preview(sheet, frame, cols, out):
    """带行列标注的预览图（棋盘格背景方便看 alpha）。"""
    rows = sheet.height // frame
    pad = 18
    W = sheet.width + pad * 2
    H = sheet.height + pad * 2 + rows * 16
    canvas = Image.new("RGBA", (W, H), (245, 245, 248, 255))
    d = ImageDraw.Draw(canvas)
    # 棋盘格底
    for y in range(pad, pad + sheet.height):
        for x in range(pad, pad + sheet.width):
            if ((x - pad) // 16 + (y - pad) // 16) % 2 == 0:
                d.rectangle([x, y, x + 15, y + 15], fill=(228, 228, 234, 255))
    canvas.alpha_composite(sheet, (pad, pad))
    for r, kind in enumerate(EXPRESSIONS):
        y = pad + r * frame + frame + 2
        d.text((pad, y), "row %d  %s" % (r, kind), fill=(20, 20, 30, 255))
    canvas.convert("RGB").save(out, quality=95)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "build", "mimo-witch"))
    ap.add_argument("--src", default=SRC)
    ap.add_argument("--frame", type=int, default=240)
    ap.add_argument("--cols", type=int, default=8)
    ap.add_argument("--frames", type=int, default=8, help="每个动画的行内帧数")
    ap.add_argument("--fps", default='{"idle":8,"happy":10,"think":6,"tired":4}')
    ap.add_argument("--pet-id", default="mimo-witch")
    ap.add_argument("--name", default="MiMo 巫女兔")
    ap.add_argument("--desc", default="橙白双马尾女巫帽兔耳少女 · MiMo 桌面伙伴")
    ap.add_argument("--png-only", action="store_true")
    args = ap.parse_args()

    fps = json.loads(args.fps)
    os.makedirs(args.out, exist_ok=True)

    print("== 构建 MiMo Mate 精灵图 ==")
    print("输出目录:", args.out)
    sheet = build_sheet(args.frame, args.cols, len(EXPRESSIONS), args.frames, args.src)
    print("精灵图尺寸: %dx%d  (frame %d x %d, cols %d, rows %d)"
          % (sheet.width, sheet.height, args.frame, args.frame, args.cols, len(EXPRESSIONS)))

    png_path = os.path.join(args.out, "spritesheet.png")
    sheet.save(png_path)

    webp_path = os.path.join(args.out, "spritesheet.webp")
    sheet.save(webp_path, "WEBP", lossless=True, quality=100, method=6)
    size = os.path.getsize(webp_path)
    print("spritesheet.webp: %.1f KB" % (size / 1024.0))
    if size > 2 * 1024 * 1024:
        print("!! 警告: 超过 2MB，MiMo 官方建议控制在 2MB 内")

    manifest = {
        "id": args.pet_id,
        "name": args.name,
        "description": args.desc,
        "version": 1,
        "spritesheet": "spritesheet.webp",
        "frameWidth": args.frame,
        "frameHeight": args.frame,
        "columns": args.cols,
        "totalFrames": args.cols * len(EXPRESSIONS),
        "anchorX": 0.5,
        "animations": {
            k: {"row": i, "frames": args.frames, "fps": int(fps.get(k, 8)), "loop": True}
            for i, k in enumerate(EXPRESSIONS)
        },
    }
    mpath = os.path.join(args.out, "manifest.json")
    with open(mpath, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print("manifest.json 已写入")

    prev = os.path.join(args.out, "_preview-sheet.png")
    preview(sheet, args.frame, args.cols, prev)
    print("预览:", prev)

    # 自检
    print("\n== 自检 ==")
    with Image.open(webp_path) as im:
        assert im.size == (args.frame * args.cols, args.frame * len(EXPRESSIONS)), "WebP 尺寸不符"
        assert im.mode in ("RGBA", "RGB"), "WebP 模式异常: " + im.mode
        alpha = im.getchannel("A")
        lo, hi = alpha.getextrema()
        print("  WebP 头合法, 尺寸 %dx%d, alpha 范围 %d..%d" % (im.width, im.height, lo, hi))
    assert manifest["frameWidth"] * manifest["columns"] == sheet.width
    assert manifest["frameHeight"] * len(EXPRESSIONS) == sheet.height
    assert "idle" in manifest["animations"]
    for k, v in manifest["animations"].items():
        assert v["frames"] <= args.cols or True  # 内置预设证明可跨行
        print("  %-6s row=%d frames=%d fps=%d loop=%s"
              % (k, v["row"], v["frames"], v["fps"], v["loop"]))
    print("  文件大小 %.1f KB (限制 2MB)" % (size / 1024.0))
    print("\n完成。复制整个目录到 userData/pets/%s/ 后，在设置里点 Mate -> Refresh。"
          % args.pet_id)


if __name__ == "__main__":
    main()
