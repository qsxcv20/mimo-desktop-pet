#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""debug_iris.py — 调试 make_blink 的虹膜自动定位，找出 happy 表情被糊块的真正原因。"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from PIL import Image

import build_anim_sheet as B  # noqa: E402


def show(expr):
    p = os.path.join(B.SRC, B.SOURCE_FILE[expr])
    full = Image.open(p).convert("RGBA").crop(B.UNION_BBOX)
    arr = np.array(full)
    print("\n=== %s (%s) ===" % (expr, B.SOURCE_FILE[expr]))
    for name, box in (("EYE_L", B.EYE_L), ("EYE_R", B.EYE_R)):
        r = B._find_iris(arr, box)
        print("  %s box=%s -> %s" % (name, box, r if not r else r[:4]))
        x0, y0, x1, y1 = box
        crop = Image.fromarray(arr[y0:y1, x0:x1]).convert("RGB")
        crop = crop.resize((crop.width // 2, crop.height // 2), Image.LANCZOS)
        out = r"D:\桌面宠物\_mimo\_dbg-iris-%s-%s.png" % (expr, name)
        crop.save(out)
        print("     眼睛框 ->", out)
        if r:
            ix0, ix1, iy0, iy1, mask = r
            if mask is not None:
                ys, xs = np.nonzero(mask)
                print("     mask 覆盖: x %d..%d  y %d..%d  像素 %d"
                      % (xs.min(), xs.max(), ys.min(), ys.max(), len(xs)))
                mm = Image.fromarray((mask * 255).astype(np.uint8))
                mm = mm.resize((mm.width // 2, mm.height // 2), Image.NEAREST)
                mo = r"D:\桌面宠物\_mimo\_dbg-mask-%s-%s.png" % (expr, name)
                mm.save(mo)
                print("     mask   ->", mo)


if __name__ == "__main__":
    for e in ("idle", "happy", "think", "tired"):
        show(e)
