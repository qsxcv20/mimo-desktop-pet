#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""install_pet.py — 安装 MiMo 桌面宠物到本机。

用法：
    python install_pet.py                 # 从 GitHub 拉取并安装
    python install_pet.py --source <目录>  # 从本地源码目录安装（离线 / 开发）
    python install_pet.py --dest <目录>   # 自定义安装目录
    python install_pet.py --no-autostart  # 不写登录自启

装完的效果：
    * 程序与素材复制到 %LOCALAPPDATA%/MiMoDesktopPet/
    * 写注册表登录自启（pythonw 静默，不弹任何终端窗口）
    * MiMo 打开 -> 桌宠自动出现；MiMo 关闭 -> 桌宠自动退出
"""

import argparse
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

DEFAULT_REPO = "https://codeload.github.com/qsxcv20/mimo-desktop-pet/zip/refs/heads/main"
DEFAULT_DEST = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
                           "MiMoDesktopPet")

REQUIRED_PY = (3, 9)
# pip 包名 -> 实际可 import 的模块名（不一样就会误报「缺依赖」）
REQUIRED_PKGS = {
    "PySide6": "PySide6",
    "pywin32": "win32api",
    "psutil": "psutil",
    "websocket-client": "websocket",
    "Pillow": "PIL",
}


def say(msg):
    print(msg)
    try:
        sys.stdout.flush()
    except Exception:
        pass


def die(msg, code=1):
    say("  !! %s" % msg)
    sys.exit(code)


def check_python():
    if sys.version_info < REQUIRED_PY:
        die("需要 Python %d.%d+，当前 %s" % (REQUIRED_PY[0], REQUIRED_PY[1],
            sys.version.split()[0]))
    say("  Python %s OK" % sys.version.split()[0])


def check_deps(install_missing=True):
    missing = []
    for pkg, mod in REQUIRED_PKGS.items():
        try:
            __import__(mod)
        except Exception:
            missing.append(pkg)
    if not missing:
        say("  依赖齐全")
        return True
    say("  缺少依赖: %s" % ", ".join(missing))
    if not install_missing:
        return False
    say("  正在 pip 安装（可能要一两分钟）...")
    r = subprocess.run([sys.executable, "-m", "pip", "install",
                       "--disable-pip-version-check"] + missing)
    return r.returncode == 0


def download_repo(url):
    say("  下载: %s" % url)
    try:
        with urllib.request.urlopen(url, timeout=120) as r:
            data = r.read()
    except Exception as e:
        die("下载失败: %s（可用 --source 指向本地目录）" % e)
    tmp = tempfile.mkdtemp(prefix="mimopet_")
    zp = os.path.join(tmp, "repo.zip")
    with open(zp, "wb") as f:
        f.write(data)
    with zipfile.ZipFile(zp) as z:
        z.extractall(tmp)
    for name in os.listdir(tmp):
        full = os.path.join(tmp, name)
        if os.path.isdir(full) and name.endswith("mimo-desktop-pet"):
            return full
    # 兜底：找含 pet/ 的那一层
    for dp, dn, fn in os.walk(tmp):
        if os.path.isfile(os.path.join(dp, "pet", "mimo_pet.py")):
            return dp
    die("下载包结构异常，找不到 pet/mimo_pet.py")


def copy_tree(src, dst, patterns):
    n = 0
    for pat in patterns:
        for p in src.glob(pat):
            if not p.is_file():
                continue
            rel = p.relative_to(src)
            out = os.path.join(dst, str(rel).replace("/", os.sep))
            os.makedirs(os.path.dirname(out), exist_ok=True)
            shutil.copy2(p, out)
            n += 1
    return n


def find_pythonw():
    base = os.path.dirname(os.path.abspath(sys.executable))
    cand = os.path.join(base, "pythonw.exe")
    if os.path.isfile(cand):
        return cand
    cand = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs",
                        "Python", "Python313", "pythonw.exe")
    if os.path.isfile(cand):
        return cand
    # 扫描所有已安装版本
    root = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Python")
    if os.path.isdir(root):
        for name in sorted(os.listdir(root), reverse=True):
            cand = os.path.join(root, name, "pythonw.exe")
            if os.path.isfile(cand):
                return cand
    return sys.executable


def set_autostart(dest, enable=True):
    import winreg
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    value_name = "MiMoDesktopPet"
    pyw = find_pythonw()
    launcher = os.path.join(dest, "tools", "launch_mimo_pet.py")
    cmd = '"%s" "%s" --watch' % (pyw, launcher)
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as k:
        if enable:
            winreg.SetValueEx(k, value_name, 0, winreg.REG_SZ, cmd)
        else:
            try:
                winreg.DeleteValue(k, value_name)
            except FileNotFoundError:
                pass
    return cmd


def stop_running(dest):
    """停掉正在跑的旧实例，避免装完有两个桌宠。

    ⚠ 只按**命令行**精确匹配 mimo_pet.py / launch_mimo_pet.py ——
    绝不能 taskkill /IM pythonw.exe，那会连用户别的 Python 程序一起杀掉。
    """
    try:
        import psutil
    except Exception:
        say("  (缺少 psutil，跳过停止旧实例)")
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
    say("  已停止 %d 个旧实例" % n)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", help="本地源码目录（含 pet/mimo_pet.py）")
    ap.add_argument("--repo", default=DEFAULT_REPO, help="GitHub zip 地址")
    ap.add_argument("--dest", default=DEFAULT_DEST, help="安装目录")
    ap.add_argument("--no-autostart", action="store_true")
    ap.add_argument("--no-launch", action="store_true")
    args = ap.parse_args()

    say("== 安装 MiMo 桌面宠物 ==")
    check_python()
    if not check_deps():
        die("依赖安装失败，请手动执行: pip install %s" % " ".join(REQUIRED_PKGS.keys()))

    src = args.source
    tmpdir = None
    if not src:
        tmpdir = tempfile.mkdtemp(prefix="mimopet_src_")
        src = download_repo(args.repo)
    if not os.path.isfile(os.path.join(src, "pet", "mimo_pet.py")):
        die("源码目录不完整: %s" % src)

    dest = os.path.abspath(args.dest)
    say("  安装到: %s" % dest)
    os.makedirs(dest, exist_ok=True)

    import pathlib
    sp = pathlib.Path(src)
    dp = pathlib.Path(dest)
    n = copy_tree(sp, dp, ["pet/*.py", "tools/*.py", "tools/*.cmd",
                           "build/mimo-witch/*", "assets/stickers/*.png",
                           "assets/stickers/index.json", "assets/stickers/src/*.jpg",
                           "start_mimo_pet.cmd", "README.md", "LICENSE",
                           "docs/*.md"])
    say("  复制 %d 个文件" % n)

    # 相对路径修正：精灵图目录写死在配置里，按实际位置改
    cfg_path = os.path.join(dest, "pet", "pet_config.json")
    try:
        cfg = json.load(open(cfg_path, "r", encoding="utf-8"))
    except Exception:
        cfg = {}
    cfg["sprite_dir"] = os.path.join(dest, "build", "mimo-witch")
    cfg["launch_mimo"] = False
    cfg["link_mimo"] = True
    cfg["exit_grace"] = 8.0
    json.dump(cfg, open(cfg_path, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    say("  已写入配置（联动模式）")

    if not args.no_autostart:
        cmd = set_autostart(dest, True)
        say("  登录自启: %s" % cmd)

    stop_running(dest)

    if not args.no_launch:
        pyw = find_pythonw()
        launcher = os.path.join(dest, "tools", "launch_mimo_pet.py")
        subprocess.Popen([pyw, launcher, "--watch"],
                         cwd=dest, creationflags=subprocess.DETACHED_PROCESS |
                         subprocess.CREATE_NEW_PROCESS_GROUP,
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
        say("  已启动联动守护（静默，无控制台窗口）")

    say("")
    say("完成。打开 MiMo 桌面应用，桌宠就会自动出现。")
    say("状态查看: python %s" % os.path.join(dest, "tools", "pet_control.py"))
    return 0


if __name__ == "__main__":
    sys.exit(main())