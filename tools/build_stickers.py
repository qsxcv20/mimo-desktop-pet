#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
build_stickers.py — 生成 MiMo 桌宠「彩蛋表情包」素材。

输入：assets/stickers/src/*.jpg（用户提供的 9 张参考图）
输出：assets/stickers/sticker-NN.png（统一 360x360 白底卡片）
     assets/stickers/index.json（顺序 / 台词 / 联动表情）

要点：
  * 参考图已经是「白底 + 角色 + 橙色描边大字」的表情包版式，
    所以**不做抠图**，直接缩放成统一尺寸的卡片，交给气泡做圆角裁切。
  * 所有源图都是 1080x1080 正方形，等比缩到 360x360 正好填满，
    白底图 = 白卡片，深色图 = 深色卡片，各自成立。
  * 台词写在 index.json 里，气泡/桌宠都从这里读，避免文案和图对不上。

用法：
    python tools/build_stickers.py
"""

import json
import os
import shutil
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass  # pythonw.exe 下 sys.stdout 是 None

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

SRC_DIR = os.path.join(ROOT, "assets", "stickers", "src")
OUT_DIR = os.path.join(ROOT, "assets", "stickers")
CARD = 360

# 源图文件名 -> (台词, 桌宠联动表情, 描述)
# 顺序即轮换顺序：从「无语思考」到「开心」再到「难过」，情绪起伏比较耐看
STICKERS = [
    ("17-38-13-042-asset_20261108-173813-042_91615725006c_216c7d19-f8bc6374a9e83c78c860b6bec4fbce4c.jpg",
     "我雷大思考怎么了", "think", "无语思考"),
    ("17-38-13-056-asset_20261108-173813-056_3ac4d1a3956b_11da75cb-082bd11ac8cbc17c4fda5e56bf181196.jpg",
     "罢工", "tired", "躺平罢工"),
    ("17-38-13-065-asset_20261108-173813-065_6ca4ea052670_31a97af7-35dc695759a35eb07364b2cdce204434.jpg",
     "困了", "tired", "打哈欠"),
    ("17-38-13-080-asset_20261108-173813-080_ee051746c8e0_733a847c-6da4104d260fc0a81fad71ae5624440e.jpg",
     "我马上就好", "idle", "拖延"),
    ("17-38-13-086-asset_20261108-173813-086_01bae83cd692_1a8ed5dd-1362d5e447a2cb010006c78691cfd8df.jpg",
     "划水摸鱼", "idle", "泡澡摸鱼"),
    ("17-38-13-095-asset_20261108-173813-095_bc20d85f779b_a4d5b22c-0cef60d6ab9c7667b24485779e39c93b.jpg",
     "好的，让我思考一下", "think", "托腮思考"),
    ("17-38-13-102-asset_20261108-173813-102_8fc8a3b0e811_9262ba8a-4bb7998a88b749f8eba0bad95723c2cb.jpg",
     "好耶！", "happy", "欢呼"),
    ("17-38-13-165-asset_20261108-173813-165_e2d0242e647f_8923472a-6a64adae2ea3f9291a0bcdc8595ffe10.jpg",
     "我太难过了", "tired", "委屈难过"),
    ("17-38-13-178-asset_20261108-173813-178_b7598af1774f_42839d30-d194a98112e110161204149dcb743d00.jpg",
     "雷军真的很香", "tired", "被窝里睡觉"),
]


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(SRC_DIR, exist_ok=True)

    index = []
    missing = []
    for i, (fname, label, mood, desc) in enumerate(STICKERS, start=1):
        src = os.path.join(SRC_DIR, fname)
        if not os.path.isfile(src):
            missing.append(fname)
            continue
        out_name = "sticker-%02d.png" % i
        out_path = os.path.join(OUT_DIR, out_name)

        im = Image.open(src).convert("RGB")
        # 等比缩放到卡片尺寸并居中（源图都是正方形，正好填满）
        im = im.resize((CARD, CARD), Image.LANCZOS)
        im.save(out_path, "PNG", optimize=True)

        # 判定是不是深色底卡：四角+边缘的平均亮度
        px = im.load()
        w, h = im.size
        samples = []
        for x in (2, w - 3, w // 2):
            for y in (2, h - 3):
                samples.append(px[x, y])
        dark = (sum(sum(c) / 3.0 for c in samples) / len(samples)) < 170

        index.append({
            "file": out_name,
            "label": label,
            "mood": mood,
            "desc": desc,
            "dark": dark,
            "src": fname,
        })
        print("  %-16s -> %-16s %d bytes  [%s / %s]%s"
              % (fname[:16], out_name, os.path.getsize(out_path), label, mood,
                 "  (深色底)" if dark else ""))

    if missing:
        print("\n缺少源图（请先复制到 %s）：" % SRC_DIR)
        for m in missing:
            print("  - " + m)
        return 1

    idx_path = os.path.join(OUT_DIR, "index.json")
    with open(idx_path, "w", encoding="utf-8") as f:
        json.dump({"card": CARD, "items": index}, f,
                  ensure_ascii=False, indent=2)
    print("\n共 %d 张，索引 -> %s" % (len(index), idx_path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
