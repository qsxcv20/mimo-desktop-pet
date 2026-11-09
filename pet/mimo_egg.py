#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
mimo_egg.py — 桌宠「彩蛋」：多点几十次气泡，就会蹦出别的表情包。

设计：
  * 用户每点一次桌宠，计数 +1。
  * 计数达到 UNLOCK_AT（默认 30）时解锁：之后**双击**桌宠，
    弹出一张「表情包贴纸」。
  * 贴纸本身带大标题（如「罢工」「困了」「划水摸鱼」），
    桌宠同时切到对应表情（think/tired/idle/happy），表情与台词联动。
  * 计数与解锁状态存到 pet/egg_state.json，跨重启保留 ——
    用户攒了 20 次结果重启就清零会很扫兴。

彩蛋气泡和普通气泡走同一个 BubbleWindow 实例，只是换成贴纸模式，
所以 owner 绑定、5 秒自动收起、再点收起这些行为完全一致。
"""

import json
import os
import random
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass  # pythonw.exe 下 sys.stdout 是 None

HERE = os.path.dirname(os.path.abspath(__file__))
STICKER_DIR = os.path.join(os.path.dirname(HERE), "assets", "stickers")
STATE_FILE = os.path.join(HERE, "egg_state.json")

UNLOCK_AT = 30          # 点多少次解锁彩蛋


class StickerPack(object):
    """加载 assets/stickers 下的贴纸卡片。"""

    def __init__(self, sticker_dir=STICKER_DIR):
        self.dir = sticker_dir
        self.items = []
        self._pixmaps = {}
        self._load()

    def _load(self):
        idx = os.path.join(self.dir, "index.json")
        if not os.path.isfile(idx):
            return
        try:
            with open(idx, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return
        for it in data.get("items", []):
            path = os.path.join(self.dir, it.get("file", ""))
            if not os.path.isfile(path):
                continue
            self.items.append({
                "file": it.get("file"),
                "path": path,
                "label": it.get("label", ""),
                "mood": it.get("mood", "idle"),
                "desc": it.get("desc", ""),
                "dark": bool(it.get("dark")),
            })

    def __len__(self):
        return len(self.items)

    def pixmap(self, item):
        """按需加载并缓存 QPixmap。"""
        from PySide6.QtGui import QPixmap
        key = item["file"]
        pm = self._pixmaps.get(key)
        if pm is None:
            pm = QPixmap(item["path"])
            self._pixmaps[key] = pm
        return pm

    def by_index(self, i):
        if not self.items:
            return None
        return self.items[i % len(self.items)]


class EggTracker(object):
    """点击计数 + 解锁状态。"""

    def __init__(self, sticker_dir=STICKER_DIR, state_file=STATE_FILE,
                 unlock_at=UNLOCK_AT):
        self.pack = StickerPack(sticker_dir)
        self.state_file = state_file
        self.unlock_at = int(unlock_at)
        self.clicks = 0
        self.unlocked = False
        self.seen = []          # 已经弹过的贴纸下标（按出现顺序）
        self._idx = 0
        self._load()

    # -- 持久化 --

    def _load(self):
        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                d = json.load(f)
            self.clicks = int(d.get("clicks") or 0)
            self.unlocked = bool(d.get("unlocked"))
            self.seen = [int(x) for x in (d.get("seen") or [])]
            self._idx = int(d.get("idx") or 0)
        except Exception:
            self.clicks = 0
            self.unlocked = False
            self.seen = []
            self._idx = 0

    def _save(self):
        try:
            tmp = self.state_file + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({"clicks": self.clicks,
                           "unlocked": self.unlocked,
                           "seen": self.seen,
                           "idx": self._idx},
                          f, ensure_ascii=False, indent=2)
            os.replace(tmp, self.state_file)
        except Exception:
            pass

    # -- 计数 --

    def __len__(self):
        """贴纸总数（代理到 pack）。"""
        return len(self.pack)

    @property
    def items(self):
        """贴纸条目列表（代理到 pack）。"""
        return self.pack.items

    def pixmap(self, item):
        """贴纸位图（代理到 pack）。"""
        return self.pack.pixmap(item)

    def by_index(self, i):
        """按序号取贴纸（代理到 pack）。"""
        return self.pack.by_index(i)

    def tap(self):
        """记一次点击（单击/双击/三击都算一次）。

        只负责计数 + 解锁判定；**不返回贴纸** ——
        贴纸由双击路径显式调用 next_sticker() 取，
        这样「单击=额度卡片、双击=表情包」的分工才干净。

        返回 dict：
            {"unlocked": bool,    本次是否刚好解锁
             "remaining": int}    距离解锁还差几次
        """
        self.clicks += 1
        just_unlocked = False

        if not self.unlocked and self.clicks >= self.unlock_at:
            self.unlocked = True
            just_unlocked = True

        self._save()
        return {
            "unlocked": just_unlocked,
            "remaining": max(0, self.unlock_at - self.clicks),
            "clicks": self.clicks,
        }

    def next_sticker(self):
        """取下一张贴纸（双击路径）。

        取过之后要立刻落盘 —— 否则「已收集哪几张」在重启后就丢了，
        贴纸轮换会从头再来。
        """
        item = self._next_sticker()
        self._save()
        return item

    def _next_sticker(self):
        """轮换下一张贴纸。优先挑没弹过的，全弹过一轮后从头再来。"""
        n = len(self.pack)
        if not n:
            return None
        unseen = [i for i in range(n) if i not in self.seen]
        if unseen:
            idx = random.choice(unseen)
        else:
            idx = self._idx % n
        self._idx = (idx + 1) % n
        self.seen.append(idx)
        if len(self.seen) > n * 2:
            self.seen = self.seen[-n:]
        return self.pack.by_index(idx)

    def hint(self):
        """当前气泡底部给不给暗示。

        2026-11-09 新交互：双击 = 抽表情包贴纸，
        三击 = 只换表情（不再出贴纸），单击 = 额度卡片。
        """
        if self.unlocked:
            return ""
        remaining = max(0, self.unlock_at - self.clicks)
        if remaining <= 5 and remaining > 0:
            return "再点 %d 下试试？" % remaining
        return ""

    def progress_text(self):
        if self.unlocked:
            return "彩蛋已解锁 · 已收集 %d 张" % len(set(self.seen))
        return "彩蛋进度 %d/%d" % (min(self.clicks, self.unlock_at),
                                   self.unlock_at)

    def reset(self):
        self.clicks = 0
        self.unlocked = False
        self.seen = []
        self._idx = 0
        self._save()


if __name__ == "__main__":
    t = EggTracker()
    print("贴纸数: %d" % len(t.pack))
    print("当前: %s" % t.progress_text())
    for it in t.pack.items:
        print("  %-16s %-14s -> %s" % (it["file"], it["label"], it["mood"]))
