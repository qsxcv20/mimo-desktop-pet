# MiMo 桌面宠物 —— 一键安装（PowerShell）
# 用法：
#   irm https://raw.githubusercontent.com/qsxcv20/mimo-desktop-pet/main/dist/install.ps1 | iex
#
# 会做三件事：
#   1. 下载仓库 zip（不需要 git）
#   2. 解压到临时目录
#   3. 调用 install_pet.py 完成安装（依赖检查 / 复制 / 注册表自启 / 启动）

$ErrorActionPreference = 'Stop'

$repo = 'qsxcv20/mimo-desktop-pet'
$zip  = Join-Path $env:TEMP 'mimo-desktop-pet.zip'
$work = Join-Path $env:TEMP 'mimo-desktop-pet-install'

Write-Host '== MiMo 桌面宠物 安装程序 ==' -ForegroundColor Cyan

# 1. 找 Python
$py = $null
foreach ($c in @('python', 'py')) {
    $cmd = Get-Command $c -ErrorAction SilentlyContinue
    if ($cmd) { $py = $cmd.Source; break }
}
if (-not $py) {
    Write-Host '  !! 没找到 Python，请先安装 Python 3.9+ 并勾选 Add to PATH' -ForegroundColor Red
    exit 1
}
Write-Host "  Python: $py"

# 2. 下载并解压
Write-Host '  下载源码...'
$url = "https://codeload.github.com/$repo/zip/refs/heads/main"
try {
    Invoke-WebRequest -Uri $url -OutFile $zip -UseBasicParsing
} catch {
    Write-Host "  !! 下载失败: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host '     可以改用 git clone 后手动执行：'
    Write-Host "       git clone https://github.com/$repo.git"
    exit 1
}
if (Test-Path $work) { Remove-Item $work -Recurse -Force }
Expand-Archive -Path $zip -DestinationPath $work -Force
$src = (Get-ChildItem $work -Directory | Select-Object -First 1).FullName
if (-not $src) { Write-Host '  !! 解压失败' -ForegroundColor Red; exit 1 }
Write-Host "  解压: $src"

# 3. 安装
$installer = Join-Path $src 'dist\skill\mimo-desktop-pet\scripts\install_pet.py'
if (-not (Test-Path $installer)) {
    Write-Host '  !! 找不到 install_pet.py' -ForegroundColor Red
    exit 1
}
& $py $installer --source $src
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ''
Write-Host '完成！打开 MiMo 桌面应用，桌宠就会自动出现。' -ForegroundColor Green