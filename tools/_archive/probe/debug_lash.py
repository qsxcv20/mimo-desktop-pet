#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""debug_lash.py — 打印眨眼用的逐列睫毛检测结果。"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from PIL import Image

import build_anim_sheet as B  # noqa: E402


def main():
    expr = sys.argv[1] if len(sys.argv) > 1 else "idle"
    which = sys.argv[2] if len(sys.argv) > 2 else "EYE_R"
    path = os.path.join(B.SRC, B.SOURCE_FILE[expr])
    arr = np.array(Image.open(path).convert("RGBA").crop(B.UNION_BBOX))
    box = getattr(B, which)
    iris = B._find_iris(arr, box)
    print("框 %s  虹膜 %s" % (box, iris[:4] if iris else None))
    if not iris:
        return
    ix0, ix1, iy0, iy1, _ = iris
    cols = B._eye_structure(arr, box, ix0, ix1, iy0, iy1)
    if not cols:
        print("结构提取失败")
        return
    print("列数 %d" % len(cols))
    print("   x  lash_top lash_bot  厚  眼底  skin            lash")
    for (x, lt, lb, skin, lash, eb) in cols:
        print("  %4d  %7d %8d %4d %5d  %-16s %s"
              % (x, lt, lb, lb - lt + 1, eb,
                 ",".join("%d" % v for v in skin.astype(int)),
                 ",".join("%d" % v for v in lash.astype(int))))


if __name__ == "__main__":
    main()
