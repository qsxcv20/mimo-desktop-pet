#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
pet_control.py — MiMo 桌宠控制 CLI

    python pet_control.py start          后台启动桌宠
    python pet_control.py stop           停止桌宠
    python pet_control.py restart        重启
    python pet_control.py status         查看状态（进程/表情/会话/连接）
    python pet_control.py set <expr>     手动表情 idle|happy|think|tired
    python pet_control.py auto           恢复跟随 MiMo 自动切换
    python pet_control.py show | hide    显示 / 隐藏
    python pet_control.py bubble         弹一次气泡
    python pet_control.py hidebubble     收起气泡（并把模式归位到「额度」）
    python pet_control.py quota          打印小米额度快照
    python pet_control.py corner <tl|tr|bl|br>   切到指定角落（测贴边）
    python pet_control.py mimo-debug     用调试端口重启 MiMo（额度读取需要）
    python pet_control.py selftest       渲染自检（不进入事件循环）

供人和 MiMo skill 共用。
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

def resolve_pet_dir():
    """桌宠程序目录：环境变量 > 本仓库同级 pet/ > 约定的默认路径。"""
    env = os.environ.get("MIMO_PET_DIR")
    if env and os.path.isdir(env):
        return env
    here = os.path.dirname(os.path.abspath(__file__))
    cand = os.path.join(os.path.dirname(here), "pet")
    if os.path.isfile(os.path.join(cand, "mimo_pet.py")):
        return cand
    return r"D:\桌面宠物\pet"


PET_DIR = resolve_pet_dir()
PET_MAIN = os.path.join(PET_DIR, "mimo_pet.py")
STATUS_FILE = os.path.join(PET_DIR, "pet_status.json")
CMD_FILE = os.path.join(PET_DIR, "pet_cmd.json")
DISABLED_FILE = os.path.join(PET_DIR, "pet_disabled")
EXPRS = ("idle", "happy", "think", "tired")


def mark_disabled(on=True):
    """写 / 清「用户主动关掉了桌宠」标记。

    有这个标记，自动恢复机制才不会把桌宠擅自拉回来 ——
    否则用户点右键「退出」之后 10 秒内它又出现了，等于关不掉。
    """
    try:
        if on:
            with open(DISABLED_FILE, "w", encoding="utf-8") as f:
                f.write("disabled at %s\n" % time.strftime("%Y-%m-%d %H:%M:%S"))
        elif os.path.isfile(DISABLED_FILE):
            os.remove(DISABLED_FILE)
    except Exception:
        pass


def read_status():
    try:
        with open(STATUS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def alive(pid):
    if not pid:
        return False
    try:
        import ctypes
        handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, int(pid))
        if handle:
            ctypes.windll.kernel32.CloseHandle(handle)
            return True
    except Exception:
        pass
    return False


def pet_alive(pid):
    """进程存在 **且** 确实是桌宠主程序。

    只看 pid 会被回收延迟骗到：刚 stop 完，pid 可能还没从系统里消失，
    do_start 就会误判成「已在运行」而根本不启动。
    """
    if not alive(pid):
        return False
    try:
        import psutil
        cmd = " ".join(psutil.Process(int(pid)).cmdline())
        return "mimo_pet.py" in cmd
    except Exception:
        return False


def send_cmd(action, **kw):
    payload = {"action": action, "ts": int(time.time() * 1000)}
    payload.update(kw)
    tmp = CMD_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    os.replace(tmp, CMD_FILE)
    return payload


def do_start():
    st = read_status()
    # 明确启动 -> 清掉「已停用」标记（否则自动恢复机制不会把它拉回来）
    mark_disabled(False)
    if st and pet_alive(st.get("pid")):
        print("桌宠已在运行 (pid=%s)" % st.get("pid"))
        return 0
    if st and alive(st.get("pid")):
        print("发现同 pid 的其它进程（不是桌宠），忽略")
    py = sys.executable
    pythonw = os.path.join(os.path.dirname(py), "pythonw.exe")
    exe = pythonw if os.path.isfile(pythonw) else py
    flags = 0
    if os.name == "nt":
        flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
    p = subprocess.Popen([exe, PET_MAIN], cwd=PET_DIR, creationflags=flags,
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
    # 等桌宠写出状态文件（最多 20 秒）
    for _ in range(80):
        time.sleep(0.25)
        st = read_status()
        if st and pet_alive(st.get("pid")):
            print("桌宠已启动 (pid=%s)" % st.get("pid"))
            return 0
        if pet_alive(p.pid) and p.pid != (st or {}).get("pid"):
            # 进程活着但状态文件还没刷新出来，再等等
            time.sleep(0.5)
            st = read_status()
            if st and pet_alive(st.get("pid")):
                print("桌宠已启动 (pid=%s)" % st.get("pid"))
                return 0
    if pet_alive(p.pid):
        print("桌宠已启动 (pid=%s，状态文件尚未刷新)" % p.pid)
        return 0
    print("启动失败（pid=%s）。请手动运行：python \"%s\"" % (p.pid, PET_MAIN))
    return 1


def do_stop():
    st = read_status()
    pid = (st or {}).get("pid")
    # 用户明确要停 -> 打标记，自动恢复机制就不会再拉回来
    mark_disabled(True)
    if not pet_alive(pid):
        print("桌宠未在运行")
        return 0
    send_cmd("quit")
    time.sleep(1.2)
    if pet_alive(pid):
        try:
            subprocess.run(["taskkill", "/PID", str(pid), "/F"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass
    # 清掉指令文件，避免下次启动时重放 quit
    try:
        os.remove(CMD_FILE)
    except Exception:
        pass
    print("桌宠已停止 (pid=%s)" % pid)
    return 0


def do_status():
    st = read_status()
    if not st:
        print("桌宠未运行（没有 %s）" % STATUS_FILE)
        return 1
    running = alive(st.get("pid"))
    print("运行中   : %s (pid=%s)" % ("是" if running else "否", st.get("pid")))
    print("当前表情 : %s" % st.get("state"))
    print("手动锁定 : %s" % (st.get("manual") or "否（跟随 MiMo）"))
    print("事件连接 : %s" % ("已连接" if st.get("connected") else "未连接"))
    print("活动会话 : %s" % (st.get("session") or "-"))
    print("最近事件 : %s" % (st.get("last_event") or "-"))
    if st.get("last_error"):
        print("连接错误 : %s" % st["last_error"])
    print("素材目录 : %s" % st.get("sprite_dir"))
    egg = st.get("egg") or {}
    if egg:
        if egg.get("unlocked"):
            print("彩蛋     : 已解锁（已收集 %d/%d）"
                  % (egg.get("collected", 0), egg.get("total", 0)))
        else:
            print("彩蛋     : %d/%d 次解锁"
                  % (egg.get("clicks", 0), egg.get("unlock_at", 30)))
    print("窗口可见 : %s" % ("是" if st.get("visible") else "否"))
    print("更新时间 : %s" % time.strftime("%H:%M:%S",
                                          time.localtime(st.get("updated", 0) / 1000)))
    return 0 if running else 1


def do_set(expr):
    if expr not in EXPRS:
        print("未知表情 %r，可选：%s" % (expr, ", ".join(EXPRS)))
        return 2
    send_cmd("set", state=expr)
    time.sleep(0.4)
    print("已切换到表情: %s" % expr)
    return 0


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    cmd = sys.argv[1].lower()
    if cmd == "start":
        return do_start()
    if cmd == "stop":
        return do_stop()
    if cmd == "restart":
        do_stop()
        time.sleep(0.6)
        return do_start()
    if cmd == "status":
        return do_status()
    if cmd == "set":
        return do_set(sys.argv[2] if len(sys.argv) > 2 else "")
    if cmd == "auto":
        send_cmd("auto")
        time.sleep(0.4)
        print("已恢复为跟随 MiMo 自动切换")
        return 0
    if cmd in ("show", "hide"):
        send_cmd(cmd)
        time.sleep(0.4)
        print("已%s" % ("显示" if cmd == "show" else "隐藏"))
        return 0
    if cmd == "autostart":
        # 重写开机自启脚本（GBK 编码，否则 cmd.exe 读中文路径会乱码）
        sc = os.path.join(os.environ.get("APPDATA", ""),
                          "Microsoft", "Windows", "Start Menu",
                          "Programs", "Startup", "MiMo桌宠.cmd")
        os.makedirs(os.path.dirname(sc), exist_ok=True)
        py = sys.executable
        pythonw = os.path.join(os.path.dirname(py), "pythonw.exe")
        exe = pythonw if os.path.isfile(pythonw) else py
        mimo_exe = os.path.join(os.environ.get("LOCALAPPDATA", ""),
                                "Programs", "Xiaomi MiMo", "Xiaomi MiMo.exe")
        port = os.environ.get("MIMO_CDP_PORT", "9333")
        lines = ["@echo off"]
        if os.path.isfile(mimo_exe):
            lines.append('start "" "%s" --updated --remote-debugging-port=%s'
                         % (mimo_exe, port))
        lines.append('start "" "%s" "%s"'
                     % (exe, os.path.join(PET_DIR, "mimo_pet.py")))
        body = "\r\n".join(lines) + "\r\n"
        with open(sc, "wb") as f:
            f.write(body.encode("gbk", errors="replace"))
        print("开机自启脚本已重写 (GBK):", sc)
        with open(sc, "rb") as f:
            raw = f.read()
        print("  原文:", raw.decode("gbk").strip().replace("\r\n", " | "))
        return 0
    if cmd == "mimo-debug":
        # 用调试端口重启 MiMo：额度读取靠 CDP 调 window.mimo.getUserUsage()
        sys.path.insert(0, os.path.join(os.path.dirname(
            os.path.abspath(__file__))))
        tools = os.path.join(os.path.dirname(os.path.abspath(__file__)))
        sys.path.insert(0, tools)
        rc = subprocess.call([sys.executable,
                              os.path.join(tools, "restart_mimo.py"),
                              "--port",
                              os.environ.get("MIMO_CDP_PORT", "9333")])
        return rc
    if cmd == "selftest":
        return subprocess.call([sys.executable, PET_MAIN, "--selftest"])
    if cmd == "bubble":
        send_cmd("bubble")
        time.sleep(1.2)
        print("已弹出气泡")
        return 0
    if cmd == "hidebubble":
        # 收起气泡，并把气泡模式归位到「额度」。
        # 测试脚本需要确定性的起点：贴纸模式下单击只是收起气泡，
        # 上一轮留下贴纸气泡的话，下一次单击就不会弹额度卡片了。
        send_cmd("hidebubble")
        time.sleep(0.8)
        print("已收起气泡")
        return 0
    if cmd == "egg":
        what = (sys.argv[2] if len(sys.argv) > 2 else "sticker").lower()
        if what not in ("sticker", "unlock", "reset"):
            print("可选：sticker | unlock | reset")
            return 2
        send_cmd("egg", what=what)
        time.sleep(1.2)
        if what == "unlock":
            print("已解锁彩蛋并弹出一张贴纸")
        elif what == "reset":
            print("彩蛋进度已重置")
        else:
            print("已抽出一张表情包贴纸")
        return 0
    if cmd == "corner":
        tag = (sys.argv[2] if len(sys.argv) > 2 else "").lower()
        if tag not in ("tl", "tr", "bl", "br"):
            print("可选：tl tr bl br")
            return 2
        send_cmd("corner", corner=tag)
        time.sleep(0.5)
        print("桌宠已移到 %s 角" % tag)
        return 0
    if cmd == "quota":
        sys.path.insert(0, PET_DIR)
        try:
            from mimo_quota import QuotaClient
        except Exception as e:
            print("无法加载额度模块: %s" % e)
            return 2
        snap = QuotaClient().get(force=True)
        print(json.dumps(snap, ensure_ascii=False, indent=2))
        print("\n-- 摘要 --")
        print("  数据来源 : %s" % snap.get("source"))
        if snap.get("error"):
            print("  提示     : %s" % snap["error"])
        if snap.get("percent") is not None:
            print("  额度剩余 : %d%%" % round(snap["percent"]))
        if snap.get("reset_date"):
            print("  额度重置 : %s" % snap["reset_date"])
        if snap.get("plan"):
            st = (snap.get("plan_status") or "").upper()
            label = snap["plan"]
            if st:
                label += "（%s）" % {
                    "ACTIVE": "生效中", "EXPIRED": "已到期",
                    "CANCELLED": "已取消", "PENDING": "待生效",
                }.get(st, st)
            print("  套餐     : %s" % label)
        if snap.get("plan_end"):
            print("  套餐到期 : %s" % snap["plan_end"])
        if snap.get("auth"):
            print("  账号状态 : %s" % snap["auth"])
        if snap.get("balance") is not None:
            print("  账户余额 : %s %s" % (snap.get("currency") or "CNY",
                                        snap.get("balance")))
        if snap.get("used"):
            print("  本轮消耗 : %s tok" % snap["used"])
        return 0
    print("未知命令: %s" % cmd)
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
