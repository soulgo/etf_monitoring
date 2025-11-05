# ============================================================
# ETF Monitor - Windows PowerShell 打包脚本
# ============================================================

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  ETF Monitor - Windows 打包工具" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查 Python
Write-Host "[1/5] 检查 Python 版本..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host $pythonVersion -ForegroundColor Green
} catch {
    Write-Host "[错误] 未找到 Python，请先安装 Python 3.8+" -ForegroundColor Red
    Read-Host "按任意键退出"
    exit 1
}

# 检查并安装依赖
Write-Host ""
Write-Host "[2/5] 检查依赖库..." -ForegroundColor Yellow

# 检查并安装项目依赖
Write-Host "检查项目依赖 (requirements.txt)..." -ForegroundColor Gray
if (Test-Path "requirements.txt") {
    pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[错误] 项目依赖安装失败" -ForegroundColor Red
        Read-Host "按任意键退出"
        exit 1
    }
    Write-Host "项目依赖已就绪" -ForegroundColor Green
} else {
    Write-Host "[警告] 未找到 requirements.txt" -ForegroundColor Yellow
}

# 检查 PyInstaller
Write-Host "检查打包工具..." -ForegroundColor Gray
$pyinstallerInstalled = pip show pyinstaller 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[提示] 未安装 PyInstaller，正在安装..." -ForegroundColor Yellow
    pip install pyinstaller
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[错误] PyInstaller 安装失败" -ForegroundColor Red
        Read-Host "按任意键退出"
        exit 1
    }
}
Write-Host "PyInstaller 已就绪" -ForegroundColor Green

# 清理旧文件
Write-Host ""
Write-Host "[3/5] 清理旧的打包文件..." -ForegroundColor Yellow
if (Test-Path "dist") {
    Remove-Item -Path "dist" -Recurse -Force
    Write-Host "已删除 dist 目录" -ForegroundColor Gray
}
if (Test-Path "build") {
    Remove-Item -Path "build" -Recurse -Force
    Write-Host "已删除 build 目录" -ForegroundColor Gray
}

# 开始打包
Write-Host ""
Write-Host "[4/5] 开始打包程序..." -ForegroundColor Yellow
Write-Host "这可能需要几分钟时间，请耐心等待..." -ForegroundColor Gray
Write-Host ""

pyinstaller --clean build.spec

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "[错误] 打包失败，请检查错误信息" -ForegroundColor Red
    Read-Host "按任意键退出"
    exit 1
}

# 检查输出文件
if (-not (Test-Path "dist\ETFMonitor.exe")) {
    Write-Host ""
    Write-Host "[错误] 未找到打包后的 exe 文件" -ForegroundColor Red
    Read-Host "按任意键退出"
    exit 1
}

# 复制额外文件
Write-Host ""
Write-Host "[5/5] 复制额外文件..." -ForegroundColor Yellow
if (Test-Path "README_DEV.md") {
    Copy-Item "README_DEV.md" "dist\README.md" -Force
    Write-Host "已复制 README.md" -ForegroundColor Gray
}
if (Test-Path "config.default.json") {
    Copy-Item "config.default.json" "dist\" -Force
    Write-Host "已复制 config.default.json" -ForegroundColor Gray
}

# 获取文件信息
$exeFile = Get-Item "dist\ETFMonitor.exe"
$fileSizeMB = [math]::Round($exeFile.Length / 1MB, 2)

# 完成
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  打包完成！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "输出位置: " -NoNewline
Write-Host "$($exeFile.FullName)" -ForegroundColor Cyan
Write-Host "文件大小: " -NoNewline
Write-Host "$fileSizeMB MB" -ForegroundColor Cyan
Write-Host ""
Write-Host "提示：" -ForegroundColor Yellow
Write-Host "- 可以将 dist 目录整体复制到其他电脑使用"
Write-Host "- 首次运行会自动创建 config.json 配置文件"
Write-Host "- 日志文件会保存在 logs 目录"
Write-Host ""
Read-Host "按任意键退出"

