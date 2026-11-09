#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
install_mate_pet.py — 把构建好的 Mate 桌宠目录安装到 MiMo Desktop 的 pets 目录，
并在安装前后做契约校验。

用法:
    python install_mate_pet.py --src D:\\桌面宠物\\build\\mimo-witch
    python install_mate_pet.py --src <dir> --userdata C:\\Users\\<you>\\AppData\\Roaming\\Xiaomi MiMo
    python install_mate_pet.py --uninstall mimo-witch
"""

import argparse, json, os, shutil, sys, time
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass  # pythonw.exe 下 sys.stdout 是 None
from PIL import Image

DEFAULT_UD = os.path.join(os.environ.get("APPDATA", ""), "Xiaomi MiMo")
REQUIRED = ("manifest.json", "spritesheet.webp")


def find_pets_dir(userdata):
    cands = [
        os.path.join(userdata, "pets"),
        os.path.join(userdata, "resources", "pets"),
    ]
    for c in cands:
        if os.path.isdir(c):
            return c
    # 兜底：创建标准位置
    std = cands[0]
    os.makedirs(std, exist_ok=True)
    return std


def validate(pet_dir):
    """按 MiMo Mate 契约校验一个 pet 目录，返回 (ok, 报告行)。"""
    rep = []
    ok = True
    for f in REQUIRED:
        p = os.path.join(pet_dir, f)
        if not os.path.isfile(p):
            rep.append("  [FAIL] 缺少必需文件 %s" % f)
            ok = False
    if not ok:
        return False, rep

    mf = os.path.join(pet_dir, "manifest.json")
    try:
        m = json.load(open(mf, encoding="utf-8"))
    except Exception as e:
        return False, ["  [FAIL] manifest.json 解析失败: %s" % e]

    for k in ("id", "name", "version", "spritesheet", "frameWidth",
              "frameHeight", "columns", "totalFrames", "animations"):
        if k not in m:
            rep.append("  [FAIL] manifest 缺少必需字段 %s" % k)
            ok = False
    if not ok:
        return False, rep

    rep.append("  id=%s  name=%s  version=%s" % (m["id"], m["name"], m["version"]))
    if m["version"] != 1:
        rep.append("  [WARN] version 官方约定恒为 1")
    if not isinstance(m["id"], str) or "-" not in m["id"] or " " in m["id"]:
        rep.append("  [WARN] id 建议使用 kebab-case")

    sp = os.path.join(pet_dir, m["spritesheet"])
    if not os.path.isfile(sp):
        rep.append("  [FAIL] manifest.spritesheet 指向的文件不存在: %s" % m["spritesheet"])
        return False, rep

    size = os.path.getsize(sp)
    rep.append("  精灵图 %s  %.1f KB" % (m["spritesheet"], size / 1024.0))
    if size > 2 * 1024 * 1024:
        rep.append("  [FAIL] 超过 2MB 上限")
        ok = False

    with open(sp, "rb") as f:
        head = f.read(16)
    if not (head[:4] == b"RIFF" and head[8:12] == b"WEBP"):
        rep.append("  [FAIL] 不是合法的 WebP (需要 RIFF....WEBP 头)")
        ok = False

    im = Image.open(sp)
    fw, fh, cols = m["frameWidth"], m["frameHeight"], m["columns"]
    anims = m["animations"]
    max_row = max(a["row"] for a in anims.values())
    exp_w, exp_h = fw * cols, fh * (max_row + 1)
    rep.append("  实际 %dx%d  期望 %dx%d (frame %dx%d x cols %d x rows %d)"
               % (im.width, im.height, exp_w, exp_h, fw, fh, cols, max_row + 1))
    if (im.width, im.height) != (exp_w, exp_h):
        rep.append("  [FAIL] 精灵图尺寸与 manifest 不一致")
        ok = False
    if im.mode not in ("RGBA", "RGB"):
        rep.append("  [FAIL] 模式 %s 不支持" % im.mode)
        ok = False
    else:
        a = im.getchannel("A").getextrema()
        if a[0] == 255:
            rep.append("  [FAIL] 没有透明像素（宠物窗口无背景，必须带 alpha）")
            ok = False
        else:
            rep.append("  alpha 范围 %d..%d ✓" % a)

    if "idle" not in anims:
        rep.append("  [FAIL] 缺少必需的 idle 动画")
        ok = False
    for k, v in sorted(anims.items()):
        rep.append("  动画 %-8s row=%d frames=%d fps=%d loop=%s"
                   % (k, v["row"], v["frames"], v["fps"], v["loop"]))

    # 帧跨行校验：内置预设 leijun 就是 4 列 8 帧跨 2 行
    for k, v in anims.items():
        if v["frames"] > cols:
            rep.append("  [NOTE] %s 的帧数(%d) > 列数(%d)，将跨行续排（内置预设即如此）"
                       % (k, v["frames"], cols))
    return ok, rep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src")
    ap.add_argument("--userdata", default=DEFAULT_UD)
    ap.add_argument("--pet-id", default=None)
    ap.add_argument("--uninstall", default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    pets_dir = find_pets_dir(args.userdata)
    print("MiMo userData :", args.userdata)
    print("pets 目录      :", pets_dir)

    if args.uninstall:
        target = os.path.join(pets_dir, args.uninstall)
        if os.path.isdir(target):
            shutil.rmtree(target)
            print("已删除:", target)
        else:
            print("不存在，跳过:", target)
        return

    if not args.src:
        ap.error("需要 --src 或 --uninstall")
    src = os.path.abspath(args.src)
    if not os.path.isdir(src):
        ap.error("源目录不存在: " + src)

    m = json.load(open(os.path.join(src, "manifest.json"), encoding="utf-8"))
    pid = args.pet_id or m["id"]
    dst = os.path.join(pets_dir, pid)

    print("\n== 源目录自检 ==")
    ok, rep = validate(src)
    for line in rep:
        print(line)
    if not ok:
        print("\n源目录未通过校验，中止安装。")
        sys.exit(1)

    if args.dry_run:
        print("\n[dry-run] 将会安装到:", dst)
        return

    # 只拷贝契约必需的两个文件，构建目录里的 png / 预览图不带进去
    if os.path.isdir(dst):
        shutil.rmtree(dst)
    os.makedirs(dst, exist_ok=True)
    for f in REQUIRED:
        shutil.copy2(os.path.join(src, f), os.path.join(dst, f))

    print("\n== 安装后复检 ==")
    ok2, rep2 = validate(dst)
    for line in rep2:
        print(line)

    print("\n安装完成 ->", dst)
    print("接下来在 MiMo Desktop 里：设置 -> Mate -> Refresh -> 选择 %s" % m["name"])


if __name__ == "__main__":
    main()
