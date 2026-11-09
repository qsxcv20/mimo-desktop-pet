#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
build_anim_sheet.py — 把静态 MiMo 立绘变成「活着」的精灵图。

不是整体缩放补间，而是分层位移场（displacement field）：

  1. 身体呼吸   下半身绕脖颈纵向微缩放 + 轻微横向扩张（squash & stretch）
  2. 发丝剪切   两侧长发水平剪切，振幅随高度递增、相位随高度滞后
                -> 发梢晚于身体到位，这是「灵动」的关键
  3. 头部轻摆   整颗头（帽/脸/身）绕脖颈点做小角度摆动
  4. 耳/帽尖    兔耳与帽冠尖端单独摆动（羽化椭圆遮罩，根部位移归零）
  5. 眨眼       眼部区域纵向压成闭合缝 + 用下方脸颊肤色补齐
  6. 情绪附加   happy 弹跳 + 落地挤压；tired 下沉 + 叹气；think 歪头

幅度标定
--------
所有幅度都以「桌宠实际显示尺寸 220px」为目标反推：
    显示缩放比 ≈ 240 / 1974 ≈ 0.1216   （精灵帧 256，内容宽 240）
    目标显示像素 -> 全分辨率像素 = 目标 / 0.1216
例：发丝摆动目标 5px -> 全分辨率 41px。

遮罩说明
--------
耳朵 / 帽尖与帽体在 alpha 上是连通的（无法用连通域分离），
所以用「羽化椭圆遮罩 + 位移衰减」：
    遮罩权重 w = clip(1 - d^2, 0, 1)，边缘位移自然归零，不会撕开接缝。

形变用 OpenCV cv2.remap 做双线性重采样，采样前做 alpha 预乘，
避免透明区颜色渗出。

用法:
    python build_anim_sheet.py --out D:\桌面宠物\build\mimo-witch
    python build_anim_sheet.py --out ... --cols 24 --frame 256
    python build_anim_sheet.py --out ... --gif     额外导出 GIF 预览
"""
import argparse
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass  # pythonw.exe 下 sys.stdout 是 None
import numpy as np
from PIL import Image

ROOT = r"D:\桌面宠物"
SRC = os.path.join(ROOT, "assets", "src")

EXPRESSIONS = ["idle", "happy", "think", "tired"]
SOURCE_FILE = {e: "mimo-%s-v2@2048.png" % e for e in EXPRESSIONS}

# ---- 统一裁剪框（四套表情同框，坐标才能复用）----
UNION_BBOX = (35, 27, 2009, 1879)
W0, H0 = UNION_BBOX[2] - UNION_BBOX[0], UNION_BBOX[3] - UNION_BBOX[1]

# ---- 眼睛框（union 坐标，已在 grid-idle.png / grid-parts.png 上人工核对）----
EYE_L = (595, 962, 842, 1170)
EYE_R = (862, 958, 1207, 1170)

# ---- 可独立摆动的部件（union 坐标椭圆：cx, cy, rx, ry）----
# 兔耳与帽冠尖端在 alpha 上和帽体连通，用羽化椭圆遮罩做局部摆动。
PARTS = {
    "ear_l":  (635, 240, 175, 225),     # 左兔耳（斜向左上）
    "ear_r":  (1340, 460, 125, 200),    # 右兔耳（帽子右侧近竖直）
    "hat_tip": (1805, 610, 140, 180),   # 帽冠上翘的尖端（右上）
    "ahoge":  (1310, 235, 90, 80),      # 头顶小翘（呆毛）
}

# ---- 每套表情的动画性格 ----
#   sway/lag : 长发剪切（全分辨率像素 / 相位滞后）
#   head     : 头部摆动角（rad）
#   breath   : 呼吸幅度系数
#   float_   : 整体上下浮动（全分辨率像素）
#   hop      : happy 跳跃高度（全分辨率像素）
#   sink     : tired 下沉（全分辨率像素）
#   ear      : 兔耳摆幅（全分辨率像素）
#   fps      : 播放帧率
PROFILE = {
    "idle":  dict(breath=0.026, sway=44.0, lag=1.30, head=0.030,
                  hop=0.0, sink=0.0, ear=26.0, tip=20.0, ahoge=14.0,
                  blink=(13, 14, 15), fps=8, float_=20.0),
    "happy": dict(breath=0.016, sway=34.0, lag=1.05, head=0.038,
                  hop=130.0, sink=0.0, ear=40.0, tip=34.0, ahoge=26.0,
                  blink=(), fps=12, float_=0.0),
    "think": dict(breath=0.022, sway=30.0, lag=1.15, head=0.046,
                  hop=0.0, sink=0.0, ear=18.0, tip=22.0, ahoge=12.0,
                  blink=(16, 17, 18), fps=6, float_=12.0),
    "tired": dict(breath=0.034, sway=20.0, lag=0.90, head=0.016,
                  hop=0.0, sink=34.0, ear=10.0, tip=10.0, ahoge=8.0,
                  blink=(8, 9, 10), fps=5, float_=14.0),
}

# 眨眼帧的闭合程度（level 越大 = 闭得越狠）
# 顺序：半闭 -> 全闭 -> 睁开一点，合成一次自然的眨眼
BLINK_LEVEL = {0: 0.42, 1: 0.62, 2: 0.22}

# happy 表情的原画本身就是「闭着的笑眼」，没有可闭的虹膜 -> 不做眨眼。
# （曾经排了 blink=(20,21)，结果 make_blink 把框角上的橙色 X 发夹当成虹膜，
#  在额头上糊出一大块肤色；另一只眼走固定比例兜底，把好好的笑眼也毁了。）

# 形变计算分辨率（相对全分辨率）。最终精灵帧只有 256px，0.55 足够且快 3 倍。
RES = 0.55


# ---------------------------------------------------------------- 眨眼

def _find_iris(arr, box):
    """在眼睛框内自动定位虹膜区域。

    用 HSV 色相段（橙 -> 黄）找虹膜，**包含虹膜底部的浅黄高光**；
    再取最大连通域排除橙色挑染的发丝。
    RGB 直接找橙会漏掉高光，导致闭眼时底部残留一块黄。
    只在框的上 78% 里找，避开脸颊腮红。
    返回 (ix0, ix1, iy0, iy1, mask|None)。
    """
    y0, x0, y1, x1 = box[1], box[0], box[3], box[2]
    H, W = arr.shape[:2]
    x1 = min(x1, W)
    y1 = min(y1, H)
    eh = y1 - y0
    ew = x1 - x0
    if eh < 10 or ew < 10:
        return None
    lim = y0 + int(eh * 0.78)
    sub = arr[y0:lim, x0:x1, :3]
    try:
        import cv2
        hsv = cv2.cvtColor(np.ascontiguousarray(sub), cv2.COLOR_RGB2HSV)
        hh, ss, vv = hsv[..., 0], hsv[..., 1], hsv[..., 2]
        # 色相在橙黄段 + 饱和度够 + **明度高**。
        # 明度这一条很关键：深棕睫毛/眼线的色相也在橙黄段、饱和度也不低，
        # 但明度只有 ~78，用 V>150 就能把它们排除，只留下橙色虹膜和浅黄高光。
        orange = ((hh >= 8) & (hh <= 42) & (ss > 50) & (vv > 150)).astype(np.uint8)
    except Exception:
        r = sub[..., 0].astype(np.int16)
        g = sub[..., 1].astype(np.int16)
        b = sub[..., 2].astype(np.int16)
        orange = ((r > 165) & (g > 75) & (g < 215) & (b < 200)).astype(np.uint8)

    ys, xs = np.nonzero(orange)
    if len(ys) < 60:
        return None

    # 取最大连通域（虹膜），排除细长的挑染发丝
    try:
        import cv2
        n, labels, stats, _ = cv2.connectedComponentsWithStats(orange, 8)
        if n > 1:
            # 按面积从大到小，逐个校验，第一个「像虹膜的」才用。
            # （最大的那块可能是橙色 X 发夹，不是虹膜。）
            order = np.argsort(-stats[1:, cv2.CC_STAT_AREA])[:6] + 1
            for k in order:
                if stats[k, cv2.CC_STAT_AREA] < 60:
                    continue
                # 先只取虹膜这一块，再在**它内部**做闭运算填掉白色高光孔洞
                # （直接对整张 mask 做闭运算会把橙色挑染的发丝和虹膜连起来）
                cm = (labels == k).astype(np.uint8)
                cm = cv2.morphologyEx(
                    cm, cv2.MORPH_CLOSE,
                    cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (45, 45)))
                ys2, xs2 = np.nonzero(cm)
                if len(ys2) < 60:
                    continue
                ix0 = x0 + int(xs2.min())
                ix1 = x0 + int(xs2.max())
                iy0 = y0 + int(ys2.min())
                iy1 = y0 + int(ys2.max())
                if not _iris_plausible(ix0, ix1, iy0, iy1, x0, y0, ew, eh):
                    continue
                # 虹膜真实形状的软遮罩（膨胀 + 羽化）
                soft = cv2.dilate(cm, np.ones((5, 5), np.uint8))
                soft = cv2.GaussianBlur(soft, (0, 0), 1.6)
                return (ix0, ix1, iy0, iy1, soft.astype(np.float32))
    except Exception:
        pass

    # 没有 cv2 时的兜底：取所有橙色像素的 bbox
    iy0, iy1 = int(ys.min()), int(ys.max())
    ix0, ix1 = int(xs.min()), int(xs.max())
    if not _iris_plausible(x0 + ix0, x0 + ix1, y0 + iy0, y0 + iy1,
                           x0, y0, ew, eh):
        return None
    return (x0 + ix0, x0 + ix1, y0 + iy0, y0 + iy1, None)


def _iris_plausible(ix0, ix1, iy0, iy1, x0, y0, ew, eh):
    """虹膜位置/尺寸是否合理。

    假的橙色来源：
      * 橙色 X 发夹 —— 正好在眼睛框的右上角
      * 橙色挑染发丝 —— 沿框的两侧
    真虹膜一定在框的中部、不贴上下边、尺寸占框的比例也有限。
    这一关是「绝不能把脸上糊出色块」的最后一道保险。
    """
    if ew <= 0 or eh <= 0:
        return False
    cw = ix1 - ix0
    ch = iy1 - iy0
    if cw < ew * 0.10 or ch < eh * 0.08:
        return False
    if cw > ew * 0.72 or ch > eh * 0.72:
        return False
    cx = (ix0 + ix1) / 2.0 - x0
    if not (ew * 0.20 <= cx <= ew * 0.80):
        return False
    if iy0 <= y0 or iy1 >= y0 + eh:          # 不能贴着框的上下边
        return False
    return True



def _eye_structure(arr, box, ix0, ix1, iy0, iy1):
    """逐列提取原画的眼睛结构。

    原画（idle 2048px）在虹膜中心列的纵向结构是：
        962..983  上眼皮皮肤   (255,237,225)
        984..993  眉毛         (216,148,135)
        994..1005 上眼皮皮肤   (255,238,225)
        1006..1033 **上睫毛**   (42,7,1) ~ (75,17,3)  ← 28px 厚的深棕带
        1034..1169 虹膜（顶部白高光 + 橙色 + 底部浅黄）
        1170..      眼睛下方的皮肤

    所以「眨眼」应该是：
      * 把**原画那 28px 厚的睫毛带**整体往下平移（而不是画一条 1px 的假线）
      * 睫毛原来的位置用**上眼皮自己的肤色**填上（不是脸颊色！脸颊带腮红，
        取中位色会变成灰紫色，一眼假）
      * 睑缘 = 睫毛带的**下沿**，天然就是原画的弧线

    返回 [(x, lash_top, lash_bot, skin_rgb, lash_rgb), ...]；
    取不到就返回 None（宁可不眨眼，也不能糊脸）。
    """
    x0, y0, x1, y1 = box
    nx0 = max(x0, ix0 - 10)
    nx1 = min(x1, ix1 + 10)
    if nx1 - nx0 < 16:
        return None

    # 眼睛下沿：从虹膜顶往下扫，直到变成皮肤
    def _eye_bottom(x):
        y = iy0
        last = iy0
        while y < y1 - 1:
            r, g, b = [int(v) for v in arr[y, x, :3]]
            sat = max(r, g, b) - min(r, g, b)
            v = max(r, g, b)
            if sat > 70 or v < 200:
                last = y
            y += 1
        return last

    cols = []
    for x in range(nx0, nx1):
        seg = arr[y0:y1, x, :3].astype(np.int16)
        V = seg.max(axis=1)
        # 从虹膜顶往上找睫毛带（这样不会被刘海/眉毛带偏），
        # 但最多往上找 40px —— 再往上就是眉毛或者刘海了。
        yy = iy0 - 1
        if yy < y0 + 2 or V[yy - y0] >= 140:
            continue
        top = yy
        while top - 1 >= y0 and V[top - 1 - y0] < 140 and yy - (top - 1) < 40:
            top -= 1
        if yy - top < 2:
            continue
        # 上眼皮肤色：睫毛带正上方 7 行（避开眉毛）
        sa = max(y0, top - 7)
        sb = max(sa + 1, top - 1)
        sb = min(sb, y1)
        if sb - sa < 2:
            continue
        skin = np.median(arr[sa:sb, x, :3].astype(np.float32), axis=0)
        if float(skin.max()) < 200:        # 采到的是头发/眉毛，不是眼皮
            continue
        # 睫毛颜色
        lash = np.median(arr[top:yy + 1, x, :3].astype(np.float32), axis=0)
        cols.append((x, top, yy, skin, lash, _eye_bottom(x)))
    if len(cols) < 12:
        return None
    return cols


def _medfilt1d(a, k=5):
    """一维中值滤波（不依赖 scipy），边缘做反射填充。"""
    if len(a) < 3:
        return np.asarray(a, dtype=np.float64)
    a = np.asarray(a, dtype=np.float64)
    k = min(int(k) | 1, len(a) | 1)
    pad = k // 2
    ext = np.concatenate([a[pad:0:-1], a, a[-2:-pad - 2:-1]])
    out = np.empty_like(a)
    for i in range(len(a)):
        out[i] = np.median(ext[i:i + k])
    return out


def _smooth1d(a, k=7):
    """一维高斯平滑（不依赖 scipy），边缘做反射填充。"""
    a = np.asarray(a, dtype=np.float64)
    if len(a) < 3:
        return a
    k = min(int(k) | 1, len(a) | 1)
    pad = k // 2
    ext = np.concatenate([a[pad:0:-1], a, a[-2:-pad - 2:-1]])
    c = np.cumsum(np.insert(ext, 0, 0.0))
    out = (c[k:] - c[:-k]) / float(k)
    return out[:len(a)]


# ------------------------------------------------------------ 眨眼：饱和暖棕睫毛带模型
#
# 关键认识（对着原画逐列实测 + 掩膜叠加图确认）：
#   * 原画里**上睫毛是一段饱和的暖棕色粗带**（RGB 约 (54,14,8)，V≈55~86），
#     紧压在虹膜上沿；而**眉毛和头发描边是灰粉棕**（约 (124,69,68)，V≈120~140）。
#     两者靠「饱和度」就能分开：(R-B) > 0.55*R 只留下睫毛。
#   * 虹膜的**暗轮廓**也是暖棕，但它在睫毛**下面**、且和睫毛之间隔着皮肤。
#     所以「每列最上面那一段暖棕」= 睫毛，不用去猜。
#   * 虹膜内部的几块白色高光会把橙色连通域切成上下几段，
#     所以先做 45x45 闭运算桥接高光，拿到**填心圆盘**。
#   * 睁眼高度 H(x) = 眼球下沿 − 眼球上沿，眼角天然收敛。
#   * 眨眼时**睫毛带整段下移**，下沿锚定在**新的睑缘**上：
#     源切片取原画的睫毛像素（粗细、弧线、纹理全部保留），
#     目标位置 = 新睑缘 − 厚度 —— 睫毛永远长在眼睑边缘上。
#     （旧版只动眼皮、睫毛原地不动，看着非常诡异。）


def _iris_disc(arr, box):
    """虹膜「填心圆盘」掩码。

    做法：
      1. 先用 _find_iris 定位虹膜（它已经做过位置/尺寸合理性校验）。
      2. 在**更大的范围**（框高 94%）里重算橙色掩码 —— _find_iris 只搜
         上 78%，会把虹膜底部的浅黄高光切掉，虹膜下沿会偏上十几像素。
      3. 取与虹膜框重叠最多的连通域，再做 45x45 闭运算：
         高光被桥接起来，圆盘连续，逐列上沿/下沿才准。
    """
    import cv2
    x0, y0, x1, y1 = box
    H, W = arr.shape[:2]
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(W, x1), min(H, y1)
    ew, eh = x1 - x0, y1 - y0
    if ew < 10 or eh < 10:
        return None
    base = _find_iris(arr, box)
    if base is None:
        return None
    ix0, ix1, iy0, iy1 = base[0], base[1], base[2], base[3]

    lim = min(y1, y0 + int(eh * 0.94))
    sub = np.ascontiguousarray(arr[y0:lim, x0:x1, :3])
    hsv = cv2.cvtColor(sub, cv2.COLOR_RGB2HSV)
    hh, ss, vv = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    orange = ((hh >= 8) & (hh <= 42) & (ss > 50) & (vv > 150)).astype(np.uint8)
    if int(orange.sum()) < 60:
        return None
    n, labels, stats, _ = cv2.connectedComponentsWithStats(orange, 8)
    if n <= 1:
        return None
    reg = labels[iy0 - y0:iy1 - y0, ix0 - x0:ix1 - x0]
    vals, cnts = np.unique(reg[reg > 0], return_counts=True)
    if len(vals) == 0:
        return None
    best = int(vals[int(np.argmax(cnts))])
    cm = (labels == best).astype(np.uint8)
    if int(cm.sum()) < 60:
        return None
    cm = cv2.morphologyEx(
        cm, cv2.MORPH_CLOSE,
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (45, 45)))
    ys2, xs2 = np.nonzero(cm)
    if len(ys2) < 60:
        return None
    nx0 = x0 + int(xs2.min())
    nx1 = x0 + int(xs2.max())
    ny0 = y0 + int(ys2.min())
    ny1 = y0 + int(ys2.max())
    if not _iris_plausible(nx0, nx1, ny0, ny1, x0, y0, ew, eh):
        return None
    # 掩码是按「框的上 94%」算的，这里补零成整个框高，方便下游直接贴
    full = np.zeros((eh, ew), np.uint8)
    full[:cm.shape[0], :] = cm
    return full


def _eye_geometry(arr, box):
    """解出眼睛几何（饱和暖棕睫毛带模型）。取不到就返回 None。

    返回 dict:
      xs      列号（绝对坐标）
      openT   眼球上沿 = 睑缘
      openB   眼球下沿
      lashT/lashB  睫毛带的上/下沿
      lashW   睫毛带厚度
      skin    上眼皮色（逐列）
      under   眼窝色（逐列）
      cBase   整只眼共用的眼睑底色
    """
    import cv2
    disc = _iris_disc(arr, box)
    if disc is None:
        return None
    x0, y0, x1, y1 = box
    H, W = arr.shape[:2]

    R = arr[:, :, 0].astype(np.int16)
    B = arr[:, :, 1].astype(np.int16)
    Bc = arr[:, :, 2].astype(np.int16)
    Vm = arr[:, :, :3].max(axis=2)

    # 睫毛 = 饱和暖棕。眉毛/头发描边是灰粉棕，(R-B) 明显偏小。
    warm = ((R - Bc) > 0.55 * R) & (Vm < 165)

    # 眼白：纯白。皮肤 (255,237,225) 饱和度 S≈30，白发偏灰，都不算。
    hsv = cv2.cvtColor(np.ascontiguousarray(arr[y0:y1, x0:x1, :3]),
                       cv2.COLOR_RGB2HSV)
    ss = hsv[..., 1]
    vv = hsv[..., 2]
    white = np.zeros((H, W), np.uint8)
    white[y0:y1, x0:x1] = ((ss <= 16) & (vv >= 246)).astype(np.uint8)
    # 开运算去掉 1~2 像素宽的杂散白点
    white = cv2.morphologyEx(
        white, cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
    # 搬运睫毛时要用的「原始白」：虹膜里的白色高光、眼白都不能被搬下去，
    # 否则 think / tired 表情会把高光拖成一条竖直白条。
    white_raw = white.copy()
    # 再按连通域面积过滤：脸上有纯白的小装饰点/高光（脸颊上的小亮点、
    # 眼睛上方的一颗小反光），它们会把「眼球上沿」顶到眉毛上去。
    # 真正的眼白是一片整块区域，面积大得多。
    nw, lw2, st2, _ = cv2.connectedComponentsWithStats(white, 8)
    keep = np.zeros(nw, bool)
    for k in range(1, nw):
        if st2[k, cv2.CC_STAT_AREA] >= 150:
            keep[k] = True
    white = keep[lw2].astype(bool)

    # 再过滤一层：**只保留与虹膜相邻的眼白**。
    # 眉毛上方、脸颊上那些纯白反光虽然面积够大，但它们离虹膜很远，
    # 一旦算进「眼球」，眼球上沿就会被顶到眉毛上去，
    # 于是「睫毛带在眼球上方」这条判据永远不成立 ——
    # think / tired 的工作区会被截掉一半，眼睛只眨一半、睫毛断成两截。
    disc_bool = np.zeros((H, W), bool)
    disc_bool[y0:y1, x0:x1] = disc.astype(bool)
    near = cv2.dilate(disc_bool.astype(np.uint8),
                      cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))) > 0
    nw3, lw4, st4, _ = cv2.connectedComponentsWithStats(
        white.astype(np.uint8), 8)
    keep2 = np.zeros(nw3, bool)
    for k in range(1, nw3):
        if st4[k, cv2.CC_STAT_AREA] >= 150:
            comp = (lw4 == k)
            if bool(np.any(comp & near)):
                keep2[k] = True
    white = keep2[lw4].astype(bool)

    # 眼球 = 虹膜圆盘 ∪ 眼白
    eyeball = np.zeros((H, W), bool)
    eyeball[y0:y1, x0:x1] = disc.astype(bool)
    eyeball |= white

    # 逐列：眼球上下沿 + 睫毛带
    cols = {}
    for i in range(disc.shape[1]):
        x = i + x0
        ys = np.nonzero(eyeball[:, x])[0]
        if len(ys) == 0:
            continue
        ot = int(ys.min())
        ob = int(ys.max())
        # 睫毛 = 该列最上面那一段暖棕
        lt = lb = -1
        y = y0
        while y < ot:
            if warm[y, x]:
                s = y
                while y < ot and warm[y, x]:
                    y += 1
                if y - s >= 3:
                    lt, lb = s, y - 1
                    break
            else:
                y += 1
        cols[x] = (ot, ob, lt, lb)
    allcols = dict(cols)
    if len(cols) < 12:
        return None

    xs = np.array(sorted(cols))
    # 最长连续段
    best_run, run_start = (0, 0), 0
    for i in range(1, len(xs)):
        if xs[i] - xs[i - 1] > 3:
            if i - run_start > best_run[1] - best_run[0]:
                best_run = (run_start, i)
            run_start = i
    if len(xs) - run_start > best_run[1] - best_run[0]:
        best_run = (run_start, len(xs))
    xs = xs[best_run[0]:best_run[1]]
    if len(xs) < 12:
        return None

    openT_raw = np.array([cols[int(x)][0] for x in xs], float)
    openB_raw = np.array([cols[int(x)][1] for x in xs], float)
    lashT_raw = np.array([cols[int(x)][2] for x in xs], float)
    lashB_raw = np.array([cols[int(x)][3] for x in xs], float)

    # ---- 有效性筛选 ----
    # 一列要参与眨眼，必须满足：
    #   * 这一列真的量到了睫毛；
    #   * 睫毛带**在眼球上方**（下沿不越过眼球上沿）——否则量到的是
    #     虹膜的暗轮廓（右眼内侧角那里，睫毛和轮廓连成一片）；
    #   * 睫毛和眼球之间那道皮肤缝不超过 56px——太远说明这一列已经
    #     跑到头发/眉毛上去了（右眼框的右侧就是刘海）。
    #     56 而不是 45：虹膜上缘那圈暗轮廓比虹膜本体暗，
    #     不会被算进「虹膜圆盘」，于是 openT 会比真实睑缘低十几像素。
    #     卡太紧的话 think / tired 的工作区会被截掉一半，
    #     眼睛只眨一半、睫毛断成两截。
    gap = openT_raw - lashB_raw
    valid = (lashT_raw >= 0) & (lashB_raw <= openT_raw - 1) & (gap <= 56)
    valid &= (openB_raw - openT_raw) >= 5
    if int(valid.sum()) < 10:
        return None
    # 把「间隔很小的两段有效列」并成一段：中间那几列量不准（多见于
    # 虹膜暗轮廓和睫毛粘在一起的地方），但只要缺口够小，
    # 用两边的值线性插值补上就行。
    # 不这么做的话，工作区会在眼睛中间断一刀 —— 左边不眨、右边眨，
    # 睫毛断成两截，比不眨眼还难看。
    GAP_BRIDGE = 14
    vidx = np.nonzero(valid)[0]
    groups = [[int(vidx[0])]]
    for i in range(1, len(vidx)):
        if vidx[i] - vidx[i - 1] <= GAP_BRIDGE + 1:
            groups[-1].append(int(vidx[i]))
        else:
            groups.append([int(vidx[i])])
    keep = max(groups, key=len)
    if len(keep) < 10:
        return None

    # 工作区 = 这一组的最左到最右，中间无效的列用插值补
    allpos = np.arange(keep[0], keep[-1] + 1)
    src = np.array(keep)
    need = len(allpos) > len(src)
    if need:
        xs = xs[allpos]
        openT_raw = np.interp(allpos, src, openT_raw[src])
        openB_raw = np.interp(allpos, src, openB_raw[src])
        lashT_raw = np.interp(allpos, src, lashT_raw[src])
        lashB_raw = np.interp(allpos, src, lashB_raw[src])
    else:
        xs = xs[src]
        openT_raw = openT_raw[src]
        openB_raw = openB_raw[src]
        lashT_raw = lashT_raw[src]
        lashB_raw = lashB_raw[src]
    n = len(xs)

    # 眼球上沿/下沿平滑：白眼球在眼角会突然断掉，中值滤波去掉尖刺
    openT = _medfilt1d(openT_raw, 5)
    openT = _smooth1d(openT, 5)
    openB = _medfilt1d(openB_raw, 5)
    openB = _smooth1d(openB, 5)

    # 厚度单独插值：上下沿各自插值会把厚度拉飞，
    # 插值出来的「厚度」一旦超上限，源切片就会把眉毛也一起搬下去。
    idx = np.arange(n)
    w_raw = lashB_raw - lashT_raw + 1.0
    w_f = _medfilt1d(w_raw, 5)
    w_f = np.clip(w_f, 6.0, 40.0)
    # 睫毛带的**上沿**才是可靠的：它和皮肤的分界永远清楚。
    # 下沿会被虹膜那圈暗轮廓污染（在 think 里两者会粘成一坨，
    # 实测厚度能从真实的 12px 虚增到 52px），所以这里只信上沿，
    # 下沿由「上沿 + 厚度」推出来。
    lt_f = _medfilt1d(lashT_raw, 5)
    lb_f = lt_f + w_f - 1.0
    # 睫毛带下沿不能低于眼球上沿（那说明量到的是别的东西）
    over = lb_f - (openT - 1.0)
    lb_f = np.minimum(lb_f, openT - 1.0)
    # 上沿被顶到眼球上沿时，厚度要跟着缩，否则会切进眼球里
    w_f = np.maximum(3.0, lb_f - lt_f + 1.0)
    lashW = w_f

    # ---- 上眼皮色：睫毛带正上方紧贴着的皮肤 ----
    skin = np.zeros((n, 3))
    for k, x in enumerate(xs):
        ref = int(lt_f[k])
        sa = max(y0, ref - 10)
        sb = max(sa + 1, ref)
        if sb - sa < 2:
            skin[k] = (255.0, 237.0, 225.0)
        else:
            skin[k] = np.median(arr[sa:sb, x, :3].astype(np.float32), axis=0)
    for c in range(3):
        col = skin[:, c]
        goodc = col > (215 if c == 0 else 190)
        if int(goodc.sum()) >= 4:
            ii = np.nonzero(goodc)[0]
            skin[:, c] = np.interp(np.arange(n), ii, col[ii])
    skin = np.stack([_smooth1d(skin[:, c], 15) for c in range(3)], axis=1)
    gm = np.median(skin, axis=0)

    # ---- 眼窝色：眼球下方（跳过下眼睑线）的皮肤 ----
    under = np.zeros((n, 3))
    for k, x in enumerate(xs):
        y = int(round(openB[k])) + 2
        while y < y1 - 3 and Vm[y, x] < 190:
            y += 1
        sa = min(y1 - 2, y)
        sb = min(y1, sa + 8)
        if sb - sa < 3:
            under[k] = skin[k]
        else:
            under[k] = np.median(arr[sa:sb, x, :3].astype(np.float32), axis=0)
    for c in range(3):
        col = under[:, c]
        goodc = col > (215 if c == 0 else 190)
        if int(goodc.sum()) >= 4:
            ii = np.nonzero(goodc)[0]
            under[:, c] = np.interp(np.arange(n), ii, col[ii])
        else:
            under[:, c] = skin[:, c]
    under = np.stack([_smooth1d(under[:, c], 15) for c in range(3)], axis=1)
    gm2 = np.median(under, axis=0)

    # ---- 睫毛正上方那条「眼皮条」 ----
    # 眨眼时腾出来的那一大块，要用**这块眼皮**拉长填上去，
    # 不能用一块平涂的肤色 —— 平涂色在 256px 里就是一条白板。
    # 肤色判别：S 在 16~70（眉毛 S≈95、白发 S≈0，都不算）、V ≥ 215。
    hsv_skin = cv2.cvtColor(np.ascontiguousarray(arr[y0:y1, x0:x1, :3]),
                            cv2.COLOR_RGB2HSV)
    sS = hsv_skin[..., 1]
    sV = hsv_skin[..., 2]
    skin_like = ((sS >= 16) & (sS <= 70) & (sV >= 215)).astype(np.uint8)
    stripTop = np.zeros(n, int)
    stripH = np.zeros(n, int)
    for k, x in enumerate(xs):
        y = int(round(lt_f[k])) - 1
        top = y
        while top > y0 and skin_like[top - 1 - y0, x - x0]:
            top -= 1
            if y - top >= 26:
                break
        stripTop[k] = top
        stripH[k] = max(0, y - top + 1)

    # 整只眼睛共用的「眼睑底色」。
    # 注意不能直接用眼皮色：原画里眼皮是脸上**偏亮的一条高光带**
    # （255,238,225），铺成一大片就会变成一块发白的方砖，在 256px 精灵帧里
    # 尤其扎眼。也不能用脸颊色：脸颊带腮红，取中位色会发灰紫。
    # 正解是取框内所有「低饱和 + 高明度」的像素 —— 那就是脸皮本身
    # （眼白纯白 S≈0 排除，灰白头发排除，腮红 S 偏高也排除）。
    sub_all = arr[y0:y1, x0:x1, :3].astype(np.uint8)
    hsv_all = cv2.cvtColor(np.ascontiguousarray(sub_all), cv2.COLOR_RGB2HSV)
    face_sel = ((hsv_all[..., 1] > 16) & (hsv_all[..., 1] < 68)
                & (hsv_all[..., 2] > 200))
    if int(face_sel.sum()) >= 200:
        face_c = np.median(sub_all[face_sel].astype(np.float32), axis=0)
    else:
        face_c = gm
    # 再压暗 6%：眼睑是一块「被睫毛压着」的皮肤，比脸颊略暗才自然；
    # 铺成一大片时如果比脸皮还亮，会读成一块白板。
    c_base = (face_c * 0.94 + gm * 0.06).astype(np.float64)

    return dict(xs=xs, openT=openT, openB=openB,
                lashT=lt_f, lashB=lb_f, lashW=lashW,
                raw=(openT_raw, openB_raw, lashT_raw, lashB_raw),
                whiteRaw=white_raw,
                skin=skin, under=under, cBase=c_base,
                stripTop=stripTop, stripH=stripH,
                dbg=(face_c, gm, gm2, face_sel.sum()),
                allcols=allcols)


def make_blink(arr, box, level=1.0):
    """眨眼：上眼睑**整体下压**，睫毛带**跟着眼睑一起走**。

    level = 1.0 完全闭眼；level 越小睁得越开。

    每列做两件事：
      1. 下压量 d(x) = level * 睁眼高度(x)。眼角处眼球本来就矮，
         d 自动趋于 0，睑缘不会断层。
      2. 把「旧睫毛顶 → 新睑缘」这一段用**原画的眼皮拉长**填上
         （不是一块平涂肤色 —— 平涂色在 256px 精灵帧里就是一条白板），
         同时把睫毛带整段**平移**到新的睑缘上 ——
         像素直接取自原画，所以粗细、弧线、纹理全部保留。
         （旧版只动眼皮、睫毛原地不动，看着非常诡异。）
    """
    H, W = arr.shape[:2]
    x0, y0, x1, y1 = box
    if x1 - x0 <= 2 or y1 - y0 <= 2 or level <= 0.001:
        return arr

    geo = _eye_geometry(arr, box)
    if geo is None:
        # 这只眼睛本来就不是睁着的（例如 happy 的闭眼笑眼）。
        # 旧版会按固定比例涂一块肤色 + 描一条睑缘线，把好好的笑眼糊成灰白。
        # 这里直接放弃：宁可不眨眼，也不能糊脸。
        return arr

    xs = geo["xs"]
    openT = geo["openT"]
    openB = geo["openB"]
    lashT = geo["lashT"]
    lashB = geo["lashB"]
    lashW = geo["lashW"]
    c_base = geo["cBase"]
    white_raw = geo["whiteRaw"]
    stripTop = geo["stripTop"]
    stripH = geo["stripH"]

    out = arr.astype(np.float32).copy()
    n = len(xs)
    for k, x in enumerate(xs):
        bot = int(round(openB[k]))
        lid = int(round(lashB[k]))          # 睑缘 = 睫毛带下沿
        height = bot - lid
        if height <= 4:
            continue

        # 左右端羽化：眼角处眼球本来就矮，但不会真的矮到 0，
        # 所以这里用一条较长的 smoothstep 窗口把下压量平滑收到 0。
        # 窗口太短会在两端留下一条竖直硬边 —— 填充区被齐刷刷切断，
        # 看着就像贴了块方砖，所以这里给到 16 列。
        edge = min(k, n - 1 - k)
        fw = 1.0 if edge >= 16 else edge / 16.0
        fw = fw * fw * (3.0 - 2.0 * fw)
        if fw <= 0.02:
            continue
        d = int(round(level * height * fw))
        # 最多闭到 88%：完全闭死会让整块眼睛变成一片空白，
        # 256px 精灵帧里看着像「脸少了一块」。留一丝虹膜反而更像眨眼。
        dmax = int(0.66 * height)
        if d > dmax:
            d = dmax
        if d <= 0:
            continue

        thickness = int(round(lashW[k]))
        if thickness < 3:
            continue
        lt = int(round(lashT[k]))
        lb = int(round(lashB[k]))
        if lb - lt + 1 < 3:
            continue

        # 睫毛带**平移** d 行：下沿锚在新的睑缘上，上沿跟着走。
        # 整段平移而不是逐列重新取样，弧线和粗细才不会走形。
        #
        # 另外闭眼越狠，睫毛带要**越粗** —— 原画里闭着的笑眼就是一条
        # 很粗的黑弯带（happy 那只眼），细线会读成「眼睛被涂白了」。
        src_h = lb - lt + 1
        dst_h = int(round(src_h * (1.0 + 0.12 * level)))
        new_lb = lid + d
        new_lt = new_lb - dst_h + 1
        if new_lt < y0 or new_lb >= H:
            continue

        # 填充区：[旧睫毛顶, 新睫毛顶)
        # 这段原来一半是睫毛、一半是虹膜，现在要变成眼皮。
        ft = max(y0, lt)
        fill_bot = new_lt
        if fill_bot <= ft:
            continue
        fill_h = fill_bot - ft

        # 填充用的眼皮：取睫毛正上方那条「眼皮条」纵向拉长。
        # 这样填出来的颜色带着原画自己的渐变（靠睫毛那侧更暗），
        # 不会变成一块死板的色块。
        st = int(stripTop[k])
        sh = int(stripH[k])
        for y in range(ft, fill_bot):
            c = c_base
            if sh >= 2:
                # 越靠下越接近原画里紧贴睫毛的那一行（最暗）。
                # 取样基准是睫毛**上沿**那一行（lt-1），
                # 不是下沿 —— 下沿是睫毛本体，取到就是一条深棕竖条。
                t = (fill_bot - 1 - y) / float(max(1, fill_h - 1))
                sy = int(round(lt - 1 - t * (sh - 1)))
                sy = max(st, min(lt - 1, sy))
                c = arr[sy, x, :3].astype(np.float32)
            # 只压暗一点点：眼皮色要跟脸皮几乎一致，
            # 否则填充区在脸上会读成一块「贴上去的方砖」。
            c = c * 0.98
            # 越靠近新睫毛越暗一点，像上眼睑的投影
            if y >= new_lt - 12:
                c = c * (1.0 - 0.14 * min(1.0, (y - (new_lt - 12)) / 12.0))
            # 上沿 5 行做过渡，避免和原皮肤之间出现横向硬边；
            # 整体再乘上羽化权重：眼角处填充完全不透明度，
            # 这样工作区左右边界不会留下一条竖直亮线。
            a = min(1.0, max(0.0, (y - ft) / 5.0)) * fw
            out[y, x, :3] = out[y, x, :3] * (1.0 - a) + c * a
            out[y, x, 3] = 255.0

        # 睫毛带搬到新睑缘上（像素取自原画，粗细/弧线/纹理全部保留）
        for j in range(dst_h):
            sy = lt + int(j * src_h / float(dst_h))
            dy = new_lt + j
            if not (0 <= sy < H and 0 <= dy < H):
                continue
            if white_raw[sy, x]:
                # 源切片里混进了纯白（虹膜的白色高光 / 眼白），
                # 绝对不能搬下去 —— think / tired 表情的虹膜高光很大，
                # 搬下去就是一条竖直白条。用眼睑底色代替。
                c = c_base
                if dy >= new_lt - 10:
                    c = c * (1.0 - 0.13 * min(1.0, (dy - (new_lt - 10)) / 10.0))
                out[dy, x, :3] = c
            else:
                out[dy, x, :3] = arr[sy, x, :3]
            out[dy, x, 3] = 255.0
    return np.clip(out, 0, 255).astype(np.uint8)


# ---------------------------------------------------------------- 位移场

def _rot(x, y, px, py, th):
    c, s = np.cos(th), np.sin(th)
    dx = (x - px) * c - (y - py) * s - (x - px)
    dy = (x - px) * s + (y - py) * c - (y - py)
    return dx, dy


def _ellipse_w(X, Y, ell):
    """羽化椭圆权重：中心 1，边缘 0。"""
    cx, cy, rx, ry = ell
    d = ((X - cx) / float(rx)) ** 2 + ((Y - cy) / float(ry)) ** 2
    return np.clip(1.0 - d, 0.0, 1.0)


def build_field(H, W, expr, phase, s=RES):
    """返回 (dx, dy) 两个 HxW float32 位移场（当前分辨率下的像素）。"""
    p = PROFILE[expr]
    u = (np.arange(W, dtype=np.float32) / float(W))[None, :]
    v = (np.arange(H, dtype=np.float32) / float(H))[:, None]
    U = np.broadcast_to(u, (H, W))
    V = np.broadcast_to(v, (H, W))
    X = U * W
    Y = V * H

    px, py = 0.50 * W, 0.60 * H
    t = phase

    # --- 1. 头部整体轻摆（绕脖颈）---
    th_head = p["head"] * np.sin(t)
    dx_h, dy_h = _rot(X, Y, px, py, th_head)

    # --- 2. 发丝剪切（两侧，振幅随高度递增，相位随高度滞后）---
    side = np.clip((np.abs(U - 0.5) - 0.185) / 0.115, 0.0, 1.0)
    ramp = np.clip((V - 0.29) / 0.56, 0.0, 1.0) ** 1.45
    lag = p["lag"] * (V - 0.29)
    sh = np.sin(2.0 * t - lag)          # 1.5 个周期/循环 -> 更灵动
    dx_s = p["sway"] * s * ramp * sh * side
    dy_s = 0.50 * p["sway"] * s * ramp * np.cos(2.0 * t - lag) * side

    # 帽区权重更高（帽檐/兔耳惯性感更强）
    hat_w = np.clip((0.455 - V) / 0.16, 0.0, 1.0)
    dx_s = dx_s * (1.0 + 0.30 * hat_w)
    dy_s = dy_s * (1.0 + 0.30 * hat_w)

    dx = dx_h + dx_s
    dy = dy_h + dy_s

    # --- 3. 呼吸：下半身绕脖颈纵向微缩放 + 横向微扩 ---
    w_body = np.clip((V - 0.55) / 0.22, 0.0, 1.0)
    bs = p["breath"] * np.sin(1.25 * t - np.pi / 2)
    dy = dy + bs * (Y - py) * w_body
    dx = dx + (0.55 * bs) * (X - px) * w_body

    # --- 4. 部件独立摆动（羽化椭圆遮罩，根部归零）---
    # 兔耳：偏上偏侧地甩，滞后于身体
    w_ear = _ellipse_w(X, Y, PARTS["ear_l"]) + _ellipse_w(X, Y, PARTS["ear_r"])
    w_ear = np.clip(w_ear, 0.0, 1.0)
    ph_ear = 2.0 * t - 0.55
    dx = dx + p["ear"] * s * w_ear * np.sin(ph_ear)
    dy = dy + 0.72 * p["ear"] * s * w_ear * np.cos(ph_ear)

    # 帽冠尖端：甩得更慢、更远
    w_tip = _ellipse_w(X, Y, PARTS["hat_tip"])
    ph_tip = 2.0 * t - 0.95
    dx = dx + p["tip"] * s * w_tip * np.sin(ph_tip)
    dy = dy + 0.62 * p["tip"] * s * w_tip * np.cos(ph_tip)

    # 呆毛：最快最轻，颤颤的感觉
    w_ah = _ellipse_w(X, Y, PARTS["ahoge"])
    ph_ah = 3.0 * t
    dx = dx + p["ahoge"] * s * w_ah * np.sin(ph_ah)
    dy = dy + 0.45 * p["ahoge"] * s * w_ah * np.cos(ph_ah)

    # --- 5. 情绪附加 ---
    if p["hop"] > 0:
        jump = max(0.0, float(np.sin(t))) ** 0.75
        dy = dy - p["hop"] * s * jump
        land = float(np.clip(1.0 - jump * 3.2, 0.0, 1.0))
        dy = dy + 26.0 * s * land
        dy = dy + (-0.034 * land) * (Y - py) * w_body
        dx = dx + (0.030 * land) * (X - px) * w_body

    if p["sink"] > 0:
        dy = dy + p["sink"] * s * (0.5 - 0.5 * np.sin(t - 0.6))

    # --- 6. 整体浮动 ---
    dy = dy + p["float_"] * s * np.sin(1.3 * t + np.pi / 2)

    return dx.astype(np.float32), dy.astype(np.float32)


_GRID_CACHE = {}

try:
    import cv2
except Exception:          # pragma: no cover
    cv2 = None


def warp(arr, dx, dy):
    """按位移场做双线性重采样（alpha 预乘避免透明区渗色）。"""
    H, W = arr.shape[:2]
    key = (H, W)
    if key not in _GRID_CACHE:
        xs = np.arange(W, dtype=np.float32)[None, :]
        ys = np.arange(H, dtype=np.float32)[:, None]
        _GRID_CACHE[key] = (xs, ys)
    xs, ys = _GRID_CACHE[key]
    map_x = xs - dx
    map_y = ys - dy

    if cv2 is not None:
        pm = arr.astype(np.float32)
        pm[..., :3] *= (pm[..., 3:4] / 255.0)
        out = cv2.remap(pm, map_x.astype(np.float32), map_y.astype(np.float32),
                        cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT,
                        borderValue=(0, 0, 0, 0))
        a = out[..., 3:4]
        rgb = np.where(a > 0.5, out[..., :3] * 255.0 / np.maximum(a, 1e-3), 0.0)
        res = np.concatenate([rgb, out[..., 3:4]], axis=2)
        np.clip(res, 0.0, 255.0, out=res)
        return res.astype(np.uint8)

    from scipy.ndimage import map_coordinates
    a = arr[..., 3].astype(np.float32) / 255.0
    rgb = arr[..., :3].astype(np.float32) * a[..., None]
    coords = np.stack([ys - dy, xs - dx])
    out = np.zeros((H, W, 4), dtype=np.float32)
    for c in range(3):
        out[..., c] = map_coordinates(np.ascontiguousarray(rgb[..., c]), coords,
                                     order=1, mode="constant", cval=0.0)
    out[..., 3] = map_coordinates(a, coords, order=1, mode="constant", cval=0.0)
    np.clip(out, 0.0, 1.0, out=out)
    return (out * 255.0 + 0.5).astype(np.uint8)


# ---------------------------------------------------------------- 组装

def place_into_frame(arr, frame, margin, bottom=0):
    """把内容图等比缩放放进 frame×frame 画布，底部对齐。"""
    H, W = arr.shape[:2]
    im = Image.fromarray(arr)
    s = min((frame - 2 * margin) / float(W),
            (frame - 2 * margin - bottom) / float(H))
    nw, nh = max(1, int(round(W * s))), max(1, int(round(H * s)))
    im = im.resize((nw, nh), Image.LANCZOS)
    canvas = Image.new("RGBA", (frame, frame), (0, 0, 0, 0))
    canvas.alpha_composite(im, (int((frame - nw) / 2), frame - margin - bottom - nh))
    return canvas


def make_preview(sheet, cols, rows, frame, out):
    prev = Image.new("RGBA", (frame * 6, frame * rows), (238, 238, 242, 255))
    for r in range(rows):
        for k, c in enumerate((0, 4, 8, 12, 16, 20)):
            if c >= cols:
                continue
            prev.alpha_composite(sheet.crop((c * frame, r * frame,
                                            (c + 1) * frame, (r + 1) * frame)),
                                (k * frame, r * frame))
    prev.convert("RGB").save(out)
    return out


def make_gif(sheet, cols, rows, frame, out, scale=2):
    """导出四个表情的 GIF 预览（半透明铺底，方便看轮廓）。"""
    for r, expr in enumerate(EXPRESSIONS):
        frames = []
        for c in range(cols):
            f = sheet.crop((c * frame, r * frame, (c + 1) * frame, (r + 1) * frame))
            bg = Image.new("RGBA", f.size, (246, 246, 250, 255))
            bg.alpha_composite(f)
            frames.append(bg.convert("P", palette=Image.ADAPTIVE, colors=64))
        p = out % expr
        frames[0].save(p, save_all=True, append_images=frames[1:],
                       duration=int(1000 / PROFILE[expr]["fps"]),
                       loop=0, optimize=True, disposal=2)
        print("  GIF:", p)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "build", "mimo-witch"))
    ap.add_argument("--src", default=SRC)
    ap.add_argument("--frame", type=int, default=256)
    ap.add_argument("--cols", type=int, default=24)
    ap.add_argument("--pet-id", default="mimo-witch")
    ap.add_argument("--name", default="MiMo 巫女兔")
    ap.add_argument("--desc", default="橙白双马尾女巫帽兔耳少女 · MiMo 桌面伙伴")
    ap.add_argument("--preview-only", action="store_true")
    ap.add_argument("--gif", action="store_true")
    ap.add_argument("--res", type=float, default=RES)
    args = ap.parse_args()

    cols = args.cols
    rows = len(EXPRESSIONS)
    frame = args.frame
    margin = max(4, frame // 32)
    res = args.res

    print("== 生成灵动精灵图 ==")
    print("帧 %dx%d, %d 帧/表情, 网格 %dx%d, 形变分辨率 %.0f%%"
          % (frame, frame, cols, cols, rows, res * 100))

    sheet = Image.new("RGBA", (frame * cols, frame * rows), (0, 0, 0, 0))
    for r, expr in enumerate(EXPRESSIONS):
        p = os.path.join(args.src, SOURCE_FILE[expr])
        full = Image.open(p).convert("RGBA").crop(UNION_BBOX)
        W0f, H0f = full.size
        w1, h1 = max(8, int(W0f * res)), max(8, int(H0f * res))
        arr_full = np.array(full)
        arr_small = np.array(full.resize((w1, h1), Image.LANCZOS))
        prof = PROFILE[expr]
        blink_at = list(prof["blink"])
        print("  %-6s 源 %dx%d -> %dx%d  blink=%s" % (expr, W0f, H0f, w1, h1, blink_at))
        for c in range(cols):
            phase = (c / float(cols)) * 2.0 * np.pi
            a = arr_small
            if c in blink_at:
                lvl = BLINK_LEVEL.get(blink_at.index(c), 1.0)
                bl = make_blink(arr_full, EYE_L, lvl)
                bl = make_blink(bl, EYE_R, lvl)
                a = np.array(Image.fromarray(bl).resize((w1, h1), Image.LANCZOS))
            dx, dy = build_field(h1, w1, expr, phase, s=res)
            a = warp(a, dx, dy)
            pm = place_into_frame(a, frame, margin)
            sheet.alpha_composite(pm, (c * frame, r * frame))
        print("         -> %d 帧已合成" % cols)

    os.makedirs(args.out, exist_ok=True)
    pp = os.path.join(args.out, "_anim-preview.png")
    make_preview(sheet, cols, rows, frame, pp)
    print("预览:", pp)

    if args.preview_only:
        return

    png = os.path.join(args.out, "spritesheet.png")
    sheet.save(png)
    webp = os.path.join(args.out, "spritesheet.webp")
    sheet.save(webp, "WEBP", lossless=True, quality=100, method=6)
    size = os.path.getsize(webp)
    print("spritesheet.webp: %.1f KB  (%dx%d)" % (size / 1024.0, sheet.width, sheet.height))
    if size > 2 * 1024 * 1024:
        print("!! 超过 2MB（MiMo Mate 契约上限）；独立桌宠不受限")

    manifest = {
        "id": args.pet_id,
        "name": args.name,
        "description": args.desc,
        "version": 1,
        "spritesheet": "spritesheet.webp",
        "frameWidth": frame,
        "frameHeight": frame,
        "columns": cols,
        "totalFrames": cols * rows,
        "anchorX": 0.5,
        "animations": {
            "idle":  {"row": 0, "frames": cols, "fps": PROFILE["idle"]["fps"],  "loop": True},
            "happy": {"row": 1, "frames": cols, "fps": PROFILE["happy"]["fps"], "loop": True},
            "think": {"row": 2, "frames": cols, "fps": PROFILE["think"]["fps"], "loop": True},
            "tired": {"row": 3, "frames": cols, "fps": PROFILE["tired"]["fps"], "loop": True},
        },
    }
    mp = os.path.join(args.out, "manifest.json")
    with open(mp, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print("manifest.json 已写入")

    if args.gif:
        make_gif(sheet, cols, rows, frame,
                 os.path.join(args.out, "_anim-%s.gif"))


if __name__ == "__main__":
    main()
