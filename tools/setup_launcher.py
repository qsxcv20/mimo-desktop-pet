#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""setup_launcher.py — 安装「一键启动 MiMo + 桌宠」的入口。

默认只装一个入口：

    桌面快捷方式「MiMo 桌宠.lnk」 -> pyw.exe -3 launch_mimo_pet.py

它指向 pyw.exe（无窗口子系统）且窗口样式为最小化，**点击不会闪黑框**。

另外两项**默认不装**，因为都会弹终端窗口：

    --with-startup  开机自启（登录时闪一个 cmd 窗口）
    --with-task     计划任务 MiMoPetGuard（每分钟闪一次 cmd 窗口）

2026-11-09：用户明确要求去掉「每分钟弹一次终端」的守护层，
所以计划任务默认不装、watchdog 也不再被自动拉起。

用法：
    python tools/setup_launcher.py                 只装桌面快捷方式
    python tools/setup_launcher.py --with-startup   再加开机自启
    python tools/setup_launcher.py --with-task      再加每分钟计划任务
    python tools/setup_launcher.py --uninstall      全部撤掉"""

import os
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass  # pythonw.exe 下 sys.stdout 是 None

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CMD = os.path.join(ROOT, "start_mimo_pet.cmd")
LAUNCHER = os.path.join(HERE, "launch_mimo_pet.py")

TASK_NAME = "MiMoPetGuard"
WRAPPER = os.path.join(HERE, "guard_task.cmd")
GUARD_LOG = os.path.join(os.environ.get("TEMP", "."), "mimo_guard.log")

STARTUP_DIR = os.path.join(os.environ.get("APPDATA", ""), "Microsoft",
                           "Windows", "Start Menu", "Programs", "Startup")
STARTUP_CMD = os.path.join(STARTUP_DIR, "MiMo桌宠.cmd")
def desktop_dir():
    """真实桌面目录。

    注意：不能用 USERPROFILE 拼 Desktop —— 桌面可能被重定向到别处
    （本机实际桌面在 Documents 下的 Workspaces 目录），那样建出来的
    快捷方式用户根本看不见。必须问系统要 CSIDL_DESKTOPDIRECTORY。
    """
    try:
        import ctypes
        buf = ctypes.create_unicode_buffer(260)
        # CSIDL_DESKTOPDIRECTORY = 0x0010
        r = ctypes.windll.shell32.SHGetFolderPathW(None, 0x0010, None, 0, buf)
        if r == 0 and buf.value:
            return buf.value
    except Exception:
        pass
    return os.path.join(os.environ.get("USERPROFILE", ""), "Desktop")


DESKTOP = desktop_dir()
SHORTCUT = os.path.join(DESKTOP, "MiMo 桌宠.lnk")
MIMO_ICON = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs",
                          "Xiaomi MiMo", "Xiaomi MiMo.exe")


def say(msg):
    print(msg)
    try:
        sys.stdout.flush()
    except Exception:
        pass


def pyw():
    """pythonw.exe 的路径（优先用版本无关的 pyw 启动器）。"""
    launcher = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs",
                            "Python", "Launcher", "pyw.exe")
    if os.path.isfile(launcher):
        return launcher
    py = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    return py if os.path.isfile(py) else sys.executable


# ---------------------------------------------------------------- 快捷方式

def make_shortcut():
    """桌面快捷方式直接指向 pyw.exe，不经过 cmd —— 避免每次点击都闪一个黑框。

    启动器的输出同时写进 pet/launcher.log，看不到控制台也有记录。
    """
    import win32com.client
    shell = win32com.client.Dispatch("WScript.Shell")
    s = shell.CreateShortcut(SHORTCUT)
    s.TargetPath = pyw()
    s.Arguments = '-3 "%s"' % LAUNCHER
    s.WorkingDirectory = ROOT
    s.Description = "启动 MiMo + MiMo 桌宠"
    s.WindowStyle = 7                     # 7 = 最小化启动
    if os.path.isfile(MIMO_ICON):
        s.IconLocation = MIMO_ICON + ",0"
    s.Save()
    return SHORTCUT


def remove_shortcut():
    if os.path.isfile(SHORTCUT):
        os.remove(SHORTCUT)
        return True
    return False


# ---------------------------------------------------------------- 开机自启

def write_startup():
    """写开机自启脚本。

    cmd.exe 在简体中文系统下按 ANSI(GBK) 读 .cmd，用 UTF-8 写会把
    中文路径弄成乱码 -> 必须写 GBK。
    """
    os.makedirs(STARTUP_DIR, exist_ok=True)
    body = '@echo off\r\nstart "" "%s"\r\n' % CMD
    with open(STARTUP_CMD, "wb") as f:
        f.write(body.encode("gbk", errors="replace"))
    return STARTUP_CMD


def remove_startup():
    if os.path.isfile(STARTUP_CMD):
        os.remove(STARTUP_CMD)
        return True
    return False


# ---------------------------------------------------------------- 计划任务

def install_task():
    """注册「每分钟跑一次 launcher」的计划任务。

    三个坑（都踩过了）：
      1. Register-ScheduledTask 在非管理员会话里报「拒绝访问」，
         所以改用 schtasks /Create（低权限可用）。
      2. schtasks 直接执行 pyw.exe 实测不生效（任务退出码 1 且
         launcher 没跑起来），套一层 .cmd 包装就正常了。
         包装脚本必须是 GBK —— cmd.exe 按 ANSI(936) 读 .cmd。
      3. schtasks 从 shell 调用会把中文路径弄坏，所以从 Python 里调
         （subprocess 走 CreateProcessW，Unicode 参数原样送达）。
    """
    exe = pyw()
    # --auto = 后台模式：用户主动关过桌宠就别再拉起来。
    # 手动跑 launcher（快捷方式 / 命令行）不带 --auto，一定把桌宠拉起来。
    body = '@echo off\r\n"%s" -3 "%s" --auto > "%s" 2>&1\r\n' % (
        exe, LAUNCHER, GUARD_LOG)
    with open(WRAPPER, "wb") as f:
        f.write(body.encode("gbk", errors="replace"))

    subprocess.run(["schtasks", "/Delete", "/TN", TASK_NAME, "/F"],
                   capture_output=True)
    r = subprocess.run(["schtasks", "/Create", "/TN", TASK_NAME,
                        "/TR", WRAPPER, "/SC", "MINUTE", "/MO", "1", "/F"],
                       capture_output=True, text=True, errors="replace")
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def remove_task():
    r = subprocess.run(["schtasks", "/Delete", "/TN", TASK_NAME, "/F"],
                       capture_output=True, text=True, errors="replace")
    if os.path.isfile(WRAPPER):
        os.remove(WRAPPER)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


# ---------------------------------------------------------------- main

def main():
    if "--uninstall" in sys.argv:
        say("撤掉快捷方式: %s" % ("已删除" if remove_shortcut() else "本来就没有"))
        say("撤掉开机自启: %s" % ("已删除" if remove_startup() else "本来就没有"))
        rc, out = remove_task()
        say("撤掉计划任务: rc=%s %s" % (rc, out.strip()[:120]))
        return 0

    say("== 安装一键启动入口 ==")

    if not os.path.isfile(CMD):
        say("  !! 缺少 %s" % CMD)
        return 1

    try:
        p = make_shortcut()
        say("  桌面快捷方式: %s" % p)
    except Exception as e:
        say("  !! 桌面快捷方式失败: %s" % e)

    if "--with-startup" in sys.argv:
        try:
            p = write_startup()
            say("  开机自启    : %s" % p)
        except Exception as e:
            say("  !! 开机自启失败: %s" % e)
    else:
        say("  开机自启    : 跳过（默认不装 —— 登录时会闪一个 cmd 窗口；")
        say("                确实要开机自动起就加 --with-startup 重跑本脚本）")

    if "--with-task" in sys.argv:
        rc, out = install_task()
        if rc == 0:
            say("  计划任务    : %s（每分钟，⚠ 会闪 cmd 窗口）" % TASK_NAME)
        else:
            say("  !! 计划任务失败 rc=%s: %s" % (rc, out.strip()[:300]))
    else:
        say("  计划任务    : 跳过（默认不装 —— 每分钟会闪一个 cmd 窗口；")
        say("                确实需要自动恢复就加 --with-task 重跑本脚本）")

    say("完成。现在可以直接双击桌面上的「MiMo 桌宠」。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
