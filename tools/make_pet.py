#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_pet.py — 一键完成：构建精灵图 → 生成动画预览 → 安装到 MiMo。

用法:
    python make_pet.py                      # 全流程（含安装）
    python make_pet.py --no-install         # 只构建 + 预览
    python make_pet.py --frames 6           # 改每行帧数
    python make_pet.py --pet-id mimo-bunny --name 'MiMo 兔巫'
"""

import argparse, os, subprocess, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass  # pythonw.exe 下 sys.stdout 是 None

ROOT = r"D:\桌面宠物"
TOOLS = os.path.join(ROOT, "tools")
DEFAULT_BUILD = os.path.join(ROOT, "build", "mimo-witch")


def run(cmd):
    print("\n$ " + " ".join(cmd))
    r = subprocess.run(cmd, shell=False)
    if r.returncode != 0:
        print("!! 失败，退出码", r.returncode)
        sys.exit(r.returncode)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pet-id", default="mimo-witch")
    ap.add_argument("--name", default="MiMo 巫女兔")
    ap.add_argument("--frames", type=int, default=8)
    ap.add_argument("--frame", type=int, default=240)
    ap.add_argument("--cols", type=int, default=8)
    ap.add_argument("--fps", default='{"idle":8,"happy":10,"think":6,"tired":4}')
    ap.add_argument("--build", default=DEFAULT_BUILD)
    ap.add_argument("--no-install", action="store_true")
    args = ap.parse_args()

    py = sys.executable
    preview_dir = os.path.join(ROOT, "build", "_preview")

    run([py, os.path.join(TOOLS, "build_mate_pet.py"),
         "--out", args.build,
         "--pet-id", args.pet_id,
         "--name", args.name,
         "--frames", str(args.frames),
         "--frame", str(args.frame),
         "--cols", str(args.cols),
         "--fps", args.fps])

    run([py, os.path.join(TOOLS, "preview_anim.py"),
         "--pet", args.build,
         "--out", preview_dir])

    if args.no_install:
        print("\n[--no-install] 跳过安装。手动安装：")
        print("  python install_mate_pet.py --src", args.build)
        return

    run([py, os.path.join(TOOLS, "install_mate_pet.py"), "--src", args.build])

    print("\n下一步：MiMo Desktop -> 设置 -> Mate -> Refresh -> 选中 %s" % args.name)


if __name__ == "__main__":
    main()
