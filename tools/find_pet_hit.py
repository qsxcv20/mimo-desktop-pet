#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
find_pet_hit.py — 算出桌宠精灵图里「角色实体」的像素分布，
                 给出实机点击该点哪里才能 100% 命中。

为什么要这个：
  桌宠窗口是 220x220 的方形，但角色只占中间一部分，
  透明区域的点击会穿透到 MiMo 底下的窗口（点不中桌宠）。
  实机连点测试如果盲点窗口正中，会有一半的点落在空白处。

输出：
  * 角色实体的包围盒（帧内坐标）
  * 躯干中心（脸/胸位置，实机点击首选）
  * 各候选点的 alpha 覆盖率

用法：
    python tools/find_pet_hit.py [表情]
"""

import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass  # pythonw.exe 下 sys.stdout 是 None

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

from PIL import Image                       # noqa: E402

SPRITE = os.path.join(ROOT, "build", "mimo-witch", "spritesheet.webp")
MANIFEST = os.path.join(ROOT, "build", "mimo-witch", "manifest.json")


def main():
    import json
    with open(MANIFEST, "r", encoding="utf-8") as f:
        m = json.load(f)
    fw = m["frameWidth"]
    fh = m["frameHeight"]
    cols = m["columns"]

    want = sys.argv[1] if len(sys.argv) > 1 else "idle"
    row = int(m["animations"][want]["row"])

    im = Image.open(SPRITE).convert("RGBA")
    # 取该行所有帧的 alpha 并集（角色在动画里会小幅移动）
    acc = [[0] * fw for _ in range(fh)]
    n = int(m["animations"][want]["frames"])
    for i in range(n):
        idx = row * cols + i
        r, c = divmod(idx, cols)
        if (r + 1) * fh > im.height:
            break
        fr = im.crop((c * fw, r * fh, (c + 1) * fw, (r + 1) * fh))
        a = fr.getchannel("A")
        px = a.load()
        for y in range(fh):
            for x in range(fw):
                if px[x, y] > 40:
                    acc[y][x] += 1

    xs = [x for x in range(fw) if any(acc[y][x] for y in range(fh))]
    ys = [y for y in range(fh) if any(acc[y][x] for x in range(fw))]
    if not xs:
        print("没有找到实体像素")
        return 1

    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    print("表情 %s：实体包围盒 x=%d..%d  y=%d..%d  (帧 %dx%d)"
          % (want, x0, x1, y0, y1, fw, fh))
    print("  归一化: x %.3f..%.3f, y %.3f..%.3f"
          % (x0 / fw, x1 / fw, y0 / fh, y1 / fh))

    # 躯干中心：取实体横截面最宽处的上 1/3（脸/胸位置）
    widths = []
    for y in range(y0, y1 + 1):
        w = sum(1 for x in range(x0, x1 + 1) if acc[y][x])
        widths.append((y, w))
    widest = max(widths, key=lambda t: t[1])[0]
    band = [t for t in widths if widest - 45 <= t[0] <= widest - 10]
    if band:
        ty = sum(t[0] for t in band) // len(band)
    else:
        ty = y0 + int((y1 - y0) * 0.3)

    # 该行的实体 x 范围
    rowxs = [x for x in range(x0, x1 + 1) if acc[ty][x]]
    if rowxs:
        tx = (min(rowxs) + max(rowxs)) // 2
    else:
        tx = (x0 + x1) // 2

    print("  躯干中心（推荐点击点）: 帧内 (%d, %d)" % (tx, ty))
    print("  归一化: (%.3f, %.3f)" % (tx / fw, ty / fh))

    # 覆盖率最高的几个点
    best = []
    for y in range(y0, y1 + 1, 4):
        for x in range(x0, x1 + 1, 4):
            best.append((acc[y][x], x, y))
    best.sort(reverse=True)
    print("  最实心区域 top5:")
    for cnt, x, y in best[:5]:
        print("    (%3d,%3d) 覆盖 %d/%d 帧" % (x, y, cnt, n))

    print("\n实机点击换算（220px 窗口，精灵图 %dx%d -> 窗口 220x220）：" % (fw, fh))
    win = 220
    print("  推荐点: 窗口内 (%d, %d)"
          % (int(tx * win / fw), int(ty * win / fh)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
