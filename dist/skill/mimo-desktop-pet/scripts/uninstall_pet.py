#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""uninstall_pet.py — 卸载 MiMo 桌面宠物。

    python uninstall_pet.py            # 停进程 + 删自启 + 删安装目录
    python uninstall_pet.py --keep-files  # 只停进程和自启，保留文件
"""

import argparse
import os
import shutil
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def say(msg):
    print(msg)
    try:
        sys.stdout.flush()
    except Exception:
        pass


def stop_processes():
    try:
        import psutil
    except Exception:
        say("  (需要 psutil 才能按命令行精确停进程，跳过)")
        return
    n = 0
    for p in psutil.process_iter(["pid", "cmdline"]):
        try:
            args = p.info["cmdline"] or []
        except Exception:
            continue
        if any(a and os.path.basename(str(a)) in
               ("mimo_pet.py", "launch_mimo_pet.py") for a in args):
            try:
                p.kill()
                n += 1
            except Exception:
                pass
    say("  已停止 %d 个进程" % n)


def remove_autostart():
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             r"Software\Microsoft\Windows\CurrentVersion\Run",
                             0, winreg.KEY_SET_VALUE) as k:
            winreg.DeleteValue(k, "MiMoDesktopPet")
        say("  已移除登录自启")
    except FileNotFoundError:
        say("  登录自启本来就没有")
    except Exception as e:
        say("  !! 移除自启失败: %s" % e)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dest", default=os.path.join(
        os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
        "MiMoDesktopPet"))
    ap.add_argument("--keep-files", action="store_true")
    args = ap.parse_args()

    say("== 卸载 MiMo 桌面宠物 ==")
    stop_processes()
    remove_autostart()
    if args.keep_files:
        say("  保留安装目录: %s" % args.dest)
    else:
        if os.path.isdir(args.dest):
            try:
                shutil.rmtree(args.dest)
                say("  已删除: %s" % args.dest)
            except Exception as e:
                say("  !! 删除失败: %s" % e)
        else:
            say("  安装目录本来就没有")
    say("完成。")
    return 0


if __name__ == "__main__":
    sys.exit(main())