---
name: mimo-desktop-pet
description: "在 MiMo 桌面应用里安装、配置、卸载「MiMo 桌面宠物」—— 一只住在 MiMo 应用窗口内部的角色桌宠：MiMo 打开时自动出现、关闭时自动退出，单击弹额度气泡、双击抽表情包贴纸、跟随 MiMo 任务状态自动变脸。Use when the user asks to install / set up / configure / uninstall the MiMo desktop pet, wants a 桌宠 / desktop pet / mascot living inside the MiMo app window, wants MiMo to show a character in its own window, or asks how to make the pet work or why it is not appearing."
icon: "🧙‍♀️"
---

# MiMo 桌面宠物

给 MiMo 桌面应用装一只住在**应用窗口内部**的角色桌宠。
它不是独立浮窗 —— 是 MiMo 主窗口的 Win32 owned window，跟着 MiMo 走、
随 MiMo 最小化而隐藏，坐标全是 MiMo 客户区坐标。

## 装完的效果

| 行为 | 说明 |
|---|---|
| MiMo 打开 | 桌宠自动出现（不用手动点任何图标）|
| MiMo 关闭 | 桌宠在 8 秒宽限期后自动退出 |
| 单击桌宠 | 弹额度气泡（小米额度 / 用量 / 当前状态）|
| 双击桌宠 | 弹一张表情包贴纸（连点 30 次解锁彩蛋）|
| 三击桌宠 | 只换表情，4 秒后自动回到「跟随 MiMo」|
| MiMo 在忙 / 出错 | 桌宠自动切 `think` / `tired` 表情 |

**全程无终端窗口** —— 用 `pythonw.exe` 静默常驻，注册表登录自启。

## 何时用这个技能

用户说「装个桌宠」「让 MiMo 窗口里有只小助手」「MiMo 桌宠怎么装 / 怎么去掉」，
或者想把 MiMo 的原生 pets 形象换成本项目的角色时。

## 怎么装

**先跑安装脚本，不要手写安装步骤。** 脚本会做依赖检查、拉源码、复制文件、
写注册表自启、改配置成联动模式，然后静默启动守护。

```powershell
python scripts\install_pet.py
```

脚本参数：

| 参数 | 用途 |
|---|---|
| `--source <目录>` | 从本地源码目录安装（离线 / 开发时用，跳过下载）|
| `--repo <zip 地址>` | 换用别的仓库源 |
| `--dest <目录>` | 换安装目录（默认 `%LOCALAPPDATA%\MiMoDesktopPet`）|
| `--no-autostart` | 不写登录自启（只临时跑一次）|
| `--no-launch` | 装完不自动启动 |

装完 **打开 MiMo 桌面应用**，桌宠就会自己出现。

## 装完必须验证

```powershell
# 1. 守护在跑、桌宠在跑、事件已连接
python "%LOCALAPPDATA%\MiMoDesktopPet\tools\pet_control.py" status

# 2. 渲染自检：素材与气泡能画出来
python "%LOCALAPPDATA%\MiMoDesktopPet\pet\mimo_pet.py" --selftest
```

`status` 里这几项要满足：`运行中 = 是`、`事件连接 = 已连接`、`窗口可见 = 是`。
再让用户看一眼 MiMo 窗口右下角，确认角色真的在里面。

## 排错

细节见 `references/使用与排错.md`。最常见的三条：

1. **桌宠不出现** —— 联动守护没跑。重跑 `install_pet.py`，
   或手动 `pythonw.exe tools\launch_mimo_pet.py --watch`。
2. **额度显示「无有效订阅」** —— 这是服务端账号订阅过期，**不是代码问题**，
   用户续订 MiMo 套餐后自动恢复，不要去改代码。
3. **脚本一启动就没了 / 日志空白** —— `pythonw.exe` 下 `sys.stdout` 是 `None`，
   `sys.stdout.reconfigure()` 会 AttributeError。所有脚本必须判空（见参考文档）。

## 卸载

```powershell
python scripts\uninstall_pet.py
```

停进程、删注册表自启、删安装目录。

## 目录

```text
scripts/install_pet.py       一键安装（依赖检查 → 拉源码 → 复制 → 写自启 → 启动）
scripts/uninstall_pet.py     卸载
references/使用与排错.md      安装路径、常用命令、排错表、两个必知技术坑
references/操作手册.md        深入开发用的操作手册（改代码 / 排错 / 验收）
```

源码本体在 GitHub 仓库 `mimo-desktop-pet`，安装脚本默认从那里拉。

---

MiMo 是小米公司的产品，本技能是第三方桌宠，与小米无关。