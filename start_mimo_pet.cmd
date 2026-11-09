@echo off
rem ============================================================
rem  MiMo 桌宠 统一启动入口
rem  - MiMo 没跑就带调试端口启动（额度气泡需要）
rem  - 桌宠没跑就拉起来
rem  - 守护层已停用（2026-11-09）：不再拉 watchdog，计划任务已删
rem  文件保持纯 ASCII，避免 cmd.exe 的 GBK/UTF-8 编码坑
rem ============================================================
setlocal
set "ROOT=%~dp0"
set "PYW=%LOCALAPPDATA%\Programs\Python\Launcher\pyw.exe"
if not exist "%PYW%" set "PYW=%LOCALAPPDATA%\Programs\Python\Python313\pythonw.exe"
if not exist "%PYW%" (
    echo [MiMo] 找不到 pythonw.exe
    pause
    exit /b 1
)
start "" "%PYW%" -3 "%ROOT%tools\launch_mimo_pet.py"
exit /b 0
