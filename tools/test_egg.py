#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
test_egg.py — 彩蛋逻辑自测（不需要 GUI）。

覆盖：
  * 点击计数累加
  * 30 次解锁
  * 解锁前不出贴纸
  * 解锁后每次点击都出贴纸
  * 贴纸轮换：未收过的优先，全收过一轮后循环
  * 状态持久化（重启后计数还在）
  * 深色底标记只有第 9 张

用法：
    python tools/test_egg.py
"""

import json
import os
import shutil
import sys
import tempfile

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass  # pythonw.exe 下 sys.stdout 是 None

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "pet"))

from mimo_egg import EggTracker, StickerPack   # noqa: E402

FAILED = []


def check(name, cond, extra=""):
    if cond:
        print("  [OK]   %s %s" % (name, extra))
    else:
        print("  [FAIL] %s %s" % (name, extra))
        FAILED.append(name)


def main():
    tmp = tempfile.mkdtemp(prefix="mimo-egg-")
    state = os.path.join(tmp, "egg_state.json")
    try:
        # -- 素材 --
        pack = StickerPack()
        check("贴纸数量 = 9", len(pack) == 9, "实际 %d" % len(pack))
        dark = [i["file"] for i in pack.items if i.get("dark")]
        check("仅第 9 张是深色底", dark == ["sticker-09.png"], str(dark))
        moods = set(i["mood"] for i in pack.items)
        check("表情联动覆盖 think/tired/idle/happy",
              moods == {"think", "tired", "idle", "happy"}, str(sorted(moods)))
        labels = [i["label"] for i in pack.items]
        check("台词都非空", all(labels), str(labels[:3]))

        # -- 计数与解锁 --
        t = EggTracker(state_file=state)
        t.reset()
        check("初始未解锁", not t.unlocked)
        check("初始计数 0", t.clicks == 0)

        # 前 29 次不产贴纸（tap 只计数，不返贴纸）
        got = [t.tap() for _ in range(29)]
        check("tap 只计数、不返贴纸",
              all("sticker" not in g for g in got))
        check("前 29 次未解锁", not t.unlocked)
        check("剩余次数提示 = 1", t.hint().find("1") >= 0, repr(t.hint()))

        # 第 30 次解锁
        g = t.tap()
        check("第 30 次解锁", g["unlocked"] is True and t.unlocked)
        # 2026-11-09：解锁提示移到气泡脚注（_render_bubble），
        # egg.hint() 只负责「还差几次」的暗示。
        check("解锁后 hint 不再提示双击（改由气泡脚注提示）",
              t.hint() == "", repr(t.hint()))

        # 解锁后用 next_sticker 取贴纸（双击路径）
        seq = []
        for _ in range(9):
            it = t.next_sticker()
            if it is None:
                FAILED.append("next_sticker 能取到贴纸")
                print("  [FAIL] next_sticker 能取到贴纸")
                break
            seq.append(it["file"])
        else:
            print("  [OK]   next_sticker 能取到贴纸")

        check("9 次取到 9 张不同的",
              len(set(seq)) == 9, "%d 张不同" % len(set(seq)))
        check("贴纸都来自贴纸包",
              all(f in [i["file"] for i in pack.items] for f in seq))
        check("收集进度 = 9", t.progress_text().find("9") >= 0,
              t.progress_text())

        # -- 持久化 --
        t2 = EggTracker(state_file=state)
        check("重启后计数保留", t2.clicks == t.clicks,
              "%d vs %d" % (t2.clicks, t.clicks))
        check("重启后解锁状态保留", t2.unlocked == t.unlocked)
        check("重启后已收集数保留",
              len(set(t2.seen)) == len(set(t.seen)))

        # -- 轮换回绕 --
        t3 = EggTracker(state_file=os.path.join(tmp, "s3.json"))
        t3.reset()
        t3.unlocked = True
        seen = []
        for _ in range(18):
            it = t3.next_sticker()
            seen.append(it["file"])
        check("超过一轮后仍在循环", len(seen) == 18)
        check("第二轮有重复（轮换生效）",
              len(set(seen[9:])) == 9, str(len(set(seen[9:]))))

        # -- hint 逻辑 --
        t4 = EggTracker(state_file=os.path.join(tmp, "s4.json"))
        t4.reset()
        for _ in range(20):
            t4.tap()
        check("离解锁 10 次时不提示", t4.hint() == "", repr(t4.hint()))
        for _ in range(5):
            t4.tap()
        check("离解锁 5 次时提示", t4.hint() != "", repr(t4.hint()))

        # -- reset --
        t4.reset()
        check("重置后计数归零", t4.clicks == 0 and not t4.unlocked)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    if FAILED:
        print("FAIL: %d 项未通过 -> %s" % (len(FAILED), FAILED))
        return 1
    print("PASS: 全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
