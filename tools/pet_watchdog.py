#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""pet_watchdog.py — MiMo 桌宠守护进程。

为什么需要它：
    桌宠和 MiMo 是两个**完全独立**的进程。桌宠启动时如果 MiMo 没跑，
    会把 MiMo 带起来（方向：桌宠 -> MiMo）；但**没有任何东西会把桌宠
    拉起来**（没有 MiMo -> 桌宠 的反向钩子），桌宠退出后也没有守护。
    所以只要桌宠崩了或者被关掉，MiMo 开着也不会再有桌宠。

本脚本常驻，每 INTERVAL 秒检查一次：
    * 桌宠在 -> 什么都不做（顺手清掉多余的重复实例）
    * 桌宠不在 -> 重新拉起它

防抖：连续拉起仍起不来（素材坏了 / 依赖缺失）就退避到 BACKOFF 秒，
     避免无限重启刷屏。

自身也要能被拉回来 —— 靠 Windows 计划任务（每分钟兜底），
所以 watchdog 自己死了也能恢复。
"""

import json
import os
import signal
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
STATUS_FILE = os.path.join(PET_DIR, "pet_status.json")
LOG_FILE = os.path.join(PET_DIR, "pet_watchdog.log")
DISABLED_FILE = os.path.join(PET_DIR, "pet_disabled")

INTERVAL = 10.0          # 多久检查一次（秒）
BACKOFF = 60.0           # 连续失败后的退避间隔（秒）
MAX_STRIKES = 3          # 连续多少次拉起失败后开始退避
START_GRACE = 30.0       # 刚拉起后的宽限期（秒）：这段时间内不重复拉


def cap_log(path, limit=512 * 1024):
    """日志超过 limit 就清空重来 —— 每分钟写一次，不封顶会一直涨。"""
    try:
        if os.path.getsize(path) > limit:
            with open(path, "w", encoding="utf-8"):
                pass
    except Exception:
        pass


def log(msg):
    line = "%s %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), msg)
    try:
        cap_log(LOG_FILE)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass
    try:
        sys.stdout.write(line)
        sys.stdout.flush()
    except Exception:
        pass


_SHELLS = ("bash.exe", "sh.exe", "cmd.exe", "powershell.exe", "pwsh.exe",
           "grep.exe", "find.exe", "conhost.exe")


def find_all(script):
    """所有正在跑 script 的进程 pid，**按启动时间倒序**（最新的在前）。

    坑 1：不能拿「命令行拼起来含 script 名」来判断 —— 任何一条 shell
          命令里提到这个文件名（比如 grep、或者检查命令本身）都会被
          误判成「它已经在跑」。所以要求 script 的文件名必须是命令行
          里的**独立一个参数**。
    坑 2：进程本身不能是 shell / grep 这类只是「提到」它的工具。
    坑 3：必须按启动时间排序。之前用 psutil 的迭代顺序取第一个，
          顺序不保证，结果「桌宠在跑」的判定和状态文件里的 pid
          对不上 -> 误判成没跑 -> 无限拉起重复实例。
    """
    name = os.path.basename(script)
    me = os.getpid()
    found = []
    try:
        import psutil
    except Exception:
        return found
    for p in psutil.process_iter(["pid", "cmdline", "name", "create_time"]):
        try:
            args = p.info["cmdline"] or []
            pid = p.info["pid"]
            exe = (p.info["name"] or "").lower()
            ctime = p.info["create_time"] or 0.0
        except Exception:
            continue
        if pid == me or exe in _SHELLS:
            continue
        if any(a and os.path.basename(a) == name for a in args):
            found.append((ctime, pid))
    found.sort(reverse=True)
    return [pid for _c, pid in found]


def find_by_script(script):
    """最新的那一个进程 pid（没有则 None）。"""
    ps = find_all(script)
    return ps[0] if ps else None


def pet_running():
    """桌宠是否在跑。

    只要存在任意一个 mimo_pet.py 进程就算在跑 —— 不要去和状态文件里的
    pid 比对，那个 pid 可能是上一个实例留下的，对不上会误判。
    """
    return bool(find_all(PET_MAIN))


def user_disabled():
    """用户主动关过桌宠 -> 不要擅自拉起来。

    没有这个判断的话，用户点右键「退出」之后 watchdog 会在 10 秒内
    把桌宠又拉起来，等于根本关不掉。
    """
    return os.path.isfile(DISABLED_FILE)


def prune(script, keep_newest=True):
    """同一脚本只应有一个实例：杀掉多余的，保留最新的。

    返回被清掉的 pid 列表。
    """
    pids = find_all(script)
    if len(pids) <= 1:
        return []
    victims = pids[1:] if keep_newest else pids[:-1]
    for pid in victims:
        try:
            os.kill(pid, signal.SIGTERM)
            log("清理重复实例 pid=%d（保留 %s）" % (pid, pids[0]))
        except Exception as e:
            log("清理 pid=%d 失败: %s" % (pid, e))
    return victims


def pythonw():
    py = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    return py if os.path.isfile(py) else sys.executable


def start_pet():
    """后台拉起桌宠。返回 True 表示拉起来了。

    写法照抄 pet_control.do_start()（实机验证过的写法）：
    stdio 全部重定向到 DEVNULL。不重定向的话子进程会继承
    watchdog 的管道句柄，watchdog 一旦退出句柄失效 -> 桌宠启动即死。
    """
    try:
        flags = 0
        if os.name == "nt":
            flags = subprocess.CREATE_NEW_PROCESS_GROUP | \
                subprocess.DETACHED_PROCESS
        subprocess.Popen(
            [pythonw(), PET_MAIN],
            cwd=PET_DIR,
            creationflags=flags,
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        log("已拉起桌宠: %s" % PET_MAIN)
        return True
    except Exception as e:
        log("拉起桌宠失败: %s" % e)
        return False


def main():
    log("watchdog 启动 (pid=%d, 间隔 %.0fs)" % (os.getpid(), INTERVAL))
    # watchdog 自己也不该有多个实例
    prune(os.path.abspath(__file__))
    strikes = 0
    next_try = 0.0
    launched_at = 0.0
    while True:
        try:
            if pet_running():
                strikes = 0
                prune(PET_MAIN)
            else:
                if user_disabled():
                    # 用户主动关过 -> 不拉起来
                    strikes = 0
                    launched_at = 0.0
                    next_try = 0.0
                else:
                    now = time.time()
                    # 刚拉起过就宽限一下，别在启动窗口内重复拉
                    if now >= next_try and (now - launched_at) > START_GRACE:
                        start_pet()
                        launched_at = now
                        strikes += 1
                        if strikes >= MAX_STRIKES:
                            log("连续 %d 次拉起仍未成功，退避 %.0fs"
                                % (strikes, BACKOFF))
                            next_try = now + BACKOFF
                            strikes = 0
                        else:
                            next_try = now + INTERVAL
        except KeyboardInterrupt:
            break
        except Exception as e:
            log("watchdog 异常: %s" % e)
        time.sleep(INTERVAL)
    log("watchdog 退出")
    return 0


if __name__ == "__main__":
    sys.exit(main())
