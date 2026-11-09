#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""launch_mimo_pet.py — 一键启动「MiMo + 桌宠」，并保证桌宠常驻。

这是用户真正会点的东西（桌面快捷方式 / 开机自启 / 计划任务都指向它）：

    1. MiMo 没跑          -> 带 --remote-debugging-port 启动（额度要靠 CDP 读）
    2. MiMo 在跑但没端口  -> 不打断它，只提示；桌宠照样能挂上去、能变脸
    3. 桌宠没跑           -> 拉起来

⚠ **守护层已停用**（2026-11-09，用户要求）：计划任务每分钟弹一次 cmd
窗口太吵 -> 计划任务 MiMoPetGuard 已删除、pet_watchdog.py 已停掉，
本脚本也不再拉它。
现在桌宠崩了**不会**自动恢复，要手动跑一次本脚本，
或 `python tools/pet_control.py start`。
想找回自动恢复：`python tools/setup_launcher.py --with-task`
（注意那条路径每分钟会弹一次 cmd 窗口）。

顺带清理重复实例：桌宠 / watchdog 都只应有一个。

注意 MiMo -> 桌宠 这一步是**运行时**完成的，不是靠这个脚本：
桌宠每 33ms 重新找一次 MiMo 宿主窗口（attach_host），
所以只要桌宠活着，你什么时候开 MiMo，桌宠都会自己挂上去。
"""

import json
import os
import subprocess
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass  # pythonw.exe 下 sys.stdout 是 None

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PET_DIR = os.path.join(ROOT, "pet")
PET_MAIN = os.path.join(PET_DIR, "mimo_pet.py")
# 守护进程已停用（2026-11-09，用户要求去掉每分钟弹窗的守护层）。
# 文件本身还留着（launcher 借它的 find_all/prune/cap_log），
# 也可以手动用 pythonw 跑它做崩溃自动恢复，只是不再自动拉起。
WATCHDOG = os.path.join(HERE, "pet_watchdog.py")
LOG_FILE = os.path.join(PET_DIR, "launcher.log")
DISABLED_FILE = os.path.join(PET_DIR, "pet_disabled")

MIMO_EXE = os.path.join(
    os.environ.get("LOCALAPPDATA", ""), "Programs", "Xiaomi MiMo",
    "Xiaomi MiMo.exe")
CDP_PORT = int(os.environ.get("MIMO_CDP_PORT", "9333"))
API_FILE = os.path.join(os.environ.get("APPDATA", ""), "Xiaomi MiMo",
                        "desktop-api.json")

# 进程检测统一走 watchdog 里的实现 —— 那里处理了「shell 命令行里提到
# 脚本名会被误判」和「psutil 迭代顺序不保证」两个坑。
sys.path.insert(0, HERE)
from pet_watchdog import (cap_log, find_all, prune,  # noqa: E402
                        user_disabled)


def say(msg):
    print(msg)
    try:
        sys.stdout.flush()
    except Exception:
        pass
    # 快捷方式走 pythonw，没有控制台 -> 同时落一份日志
    try:
        cap_log(LOG_FILE)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), msg))
    except Exception:
        pass


def mimo_running():
    """MiMo 是否在跑（主进程 pid 优先，窗口兜底）。"""
    try:
        with open(API_FILE, "r", encoding="utf-8") as f:
            pid = int(json.load(f).get("pid") or 0)
        if pid:
            try:
                import psutil
                if psutil.Process(pid).is_running():
                    return True
            except Exception:
                pass
    except Exception:
        pass
    sys.path.insert(0, PET_DIR)
    try:
        import mimo_host as H
        return H.find_mimo_window(timeout=0, include_hidden=True) is not None
    except Exception:
        return False


def cdp_ok():
    """MiMo 是否带调试端口在跑（额度读取的前提）。"""
    try:
        sys.path.insert(0, PET_DIR)
        from mimo_cdp import MiMoCDP
        return MiMoCDP(port=CDP_PORT).available()
    except Exception:
        return False


def pythonw():
    py = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    return py if os.path.isfile(py) else sys.executable


def spawn(script):
    """后台拉起一个 pythonw 脚本。

    写法照抄 pet_control.do_start() —— 那套已经被实机验证过：
      * 用 pythonw.exe（GUI 子系统，不弹控制台）
      * stdio 全部重定向到 DEVNULL
      * cwd 放到脚本所在目录

    不重定向 stdio 的话，子进程会继承父进程的管道句柄，
    父进程一退出句柄就失效 -> 子进程启动即死。
    """
    try:
        flags = 0
        if os.name == "nt":
            flags = subprocess.CREATE_NEW_PROCESS_GROUP | \
                subprocess.DETACHED_PROCESS
        subprocess.Popen(
            [pythonw(), script],
            cwd=os.path.dirname(os.path.abspath(script)),
            creationflags=flags,
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except Exception as e:
        say("  !! 启动失败: %s" % e)
        return False


def wait_for(script, timeout=15.0):
    """等脚本真正跑起来（进程出现即算），返回 pid 或 None。"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        pids = find_all(script)
        if pids:
            return pids[0]
        time.sleep(0.4)
    return None


def start_mimo():
    if not os.path.isfile(MIMO_EXE):
        say("  !! 找不到 MiMo: %s" % MIMO_EXE)
        return False
    args = [MIMO_EXE, "--updated", "--remote-debugging-port=%d" % CDP_PORT]
    try:
        subprocess.Popen(args, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
        say("  已启动 MiMo（调试端口 %d）" % CDP_PORT)
        # 自己拉起来的 MiMo 必须把窗口叫出来
        if show_mimo_window(timeout=15.0):
            say("  MiMo 窗口已显示")
        else:
            say("  !! MiMo 进程起来了但窗口还是隐藏的，"
                "手动跑 `python pet/show_mimo.py` 唤出来")
        return True
    except Exception as e:
        say("  !! 启动 MiMo 失败: %s" % e)
        return False


def show_mimo_window(timeout=12.0):
    """把 MiMo 主窗口显示出来（公共实现见 pet/mimo_host.py）。

    只在**我们自己启动 MiMo** 的时候调用：MiMo 已经在跑的时候不动它，
    否则用户自己收到托盘里、想安静用 MiMo，每分钟都会被强行拽出来。
    """
    sys.path.insert(0, PET_DIR)
    try:
        import mimo_host as H
    except Exception:
        return False
    return H.show_mimo_window(timeout=timeout)


def ensure(script, label):
    """保证 script 有一个实例在跑；多了就清掉多余的。"""
    pids = find_all(script)
    if len(pids) > 1:
        killed = prune(script)
        if killed:
            say("  %s: 清掉 %d 个重复实例" % (label, len(killed)))
    if pids:
        say("  %s: 已在运行 (pid=%s)" % (label, pids[0]))
        return pids[0]
    say("  %s: 未运行 -> 启动" % label)
    spawn(script)
    pid = wait_for(script)
    say("  %s: %s" % (label, ("已启动 (pid=%s)" % pid if pid else "启动失败")))
    return pid


def watch_loop():
    """联动守护：MiMo 开 -> 自动唤醒桌宠；MiMo 关 -> 桌宠自己退出。

    这是被删掉的 pet_watchdog.py 的替代品，但逻辑反过来：
    以前是「桌宠死了就拉」，现在以 MiMo 的生死为准绳 —— MiMo 不在，
    桌宠就没有存在的意义。桌宠侧靠 link_mimo + exit_grace 自己退出。
    """
    say("== 联动守护模式 ==")
    say("  MiMo 开启 -> 自动唤醒桌宠；MiMo 关闭 -> 桌宠自动退出")
    say("  关掉本进程（或结束任务管理器里的 pythonw）即可停掉守护")
    while True:
        try:
            pids = find_all(PET_MAIN)
            if mimo_running():
                if not pids and not user_disabled():
                    say("  检测到 MiMo 在跑 -> 拉起桌宠")
                    spawn(PET_MAIN)
                    time.sleep(8.0)
            time.sleep(2.0)
        except KeyboardInterrupt:
            say("  守护退出")
            return 0
        except Exception as e:
            say("  !! 守护循环异常: %s" % e)
            time.sleep(2.0)


def main():
    # --auto = 后台模式（计划任务每分钟调）：用户主动关过桌宠就别再拉。
    # 不带 --auto = 用户明确点快捷方式 / 命令行启动：一定把桌宠拉起来。
    auto = "--auto" in sys.argv
    say("== MiMo 桌宠 一键启动%s ==" % ("（后台模式）" if auto else ""))

    if "--watch" in sys.argv:
        return watch_loop()

    if auto and os.path.isfile(DISABLED_FILE):
        say("  用户已关闭桌宠 -> 本次不做任何事（要重新开启：手动跑一次本脚本）")
        return 0

    if not auto:
        # 明确启动 -> 清掉「已停用」标记
        try:
            if os.path.isfile(DISABLED_FILE):
                os.remove(DISABLED_FILE)
                say("  已清除「桌宠已停用」标记")
        except Exception:
            pass

    # 1. MiMo
    if mimo_running():
        say("  MiMo: 已在运行")
        if not cdp_ok():
            say("  !     没有调试端口 %d -> 额度气泡读不到数。" % CDP_PORT)
            say("  !     需要额度就在桌宠右键菜单选「重启 MiMo（启用额度读取）」。")
    else:
        say("  MiMo: 未运行 -> 启动")
        start_mimo()
        time.sleep(3.0)

    # 2. 桌宠
    ensure(PET_MAIN, "桌宠")

    # 3. watchdog —— 已停用（2026-11-09）。
    #    计划任务每分钟弹 cmd 窗口太吵，用户要求去掉，计划任务已删。
    #    桌宠崩了不会自动恢复，需要手动跑本脚本。
    #    要恢复：`python tools/setup_launcher.py --with-task`

    say("完成。等几秒后用 `python tools/pet_control.py status` 看状态。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
