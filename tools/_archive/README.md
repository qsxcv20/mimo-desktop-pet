# tools/_archive — 归档脚本（不参与运行）

这里的脚本**不会被 launcher / watchdog / 计划任务调用**，也不需要维护。
它们是开发 MiMo 桌宠过程中的**调研与探针记录**，留着是为了以后接手的人
知道「这条路已经走过了、结论是什么」，不用再从头逆向一遍。

## 目录

| 子目录 | 内容 | 什么时候还会用到 |
|---|---|---|
| `research/` | MiMo 内部逆向成果：`scan_*`（扫 bundle / API 路由 / IPC）、`hunt_*`（找认证链路）、`cdp_*`（调试端口）、`trace_*` / `dbg_*`（SSO 调试）、`probe_quota*` / `probe_platform*`（额度与账户层） | **额度功能还没做完**（服务端订阅 EXPIRED，需用户续订）。续订后如果 API 又变了，从这里开始查 |
| `probe/` | 一次性调试探针：眨眼像素分析、眼睛网格、裁图、dump、face_grid、早期 dblclick 探针等 | 基本不会再用；留作「当时怎么定位的」记录 |

## 规则

- 归档脚本里的相对路径假设**已失效**（原脚本假设自己在 `tools/` 下运行，现在在 `tools/_archive/<子目录>/` 下）。要跑请先移回 `tools/`。
- `tools/` 根目录现在只留 **57 个**真正在用的脚本：全部 `test_*.py` + 运行时（`pet_control.py` / `launch_mimo_pet.py` / `pet_watchdog.py` / `force_front.py` / `shot_mimo.py` / `restart_mimo.py` / `setup_launcher.py` / `grab_window.py` / `check_deps.py`）+ 素材流水线（`build_*_sheet.py` / `build_stickers.py` / `render_eggs.py` / `install_mate_pet.py` / `export_pet.py` / `make_pet.py` / `pet_frames.py` / `make_demo_gif.py` / `capture_creds.py` / `restore_mimo.py`）+ 文档引用的复现脚本。
- **不要在 `tools/` 根目录堆新的一次性脚本**；写完探针就丢进 `probe/`，逆向就丢进 `research/`。
- 归档 ≠ 删除。文件全部还在，只是挪了位置。
