param(
    [string]$Action = "start"
)

$ErrorActionPreference = "Stop"
$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$BackendDir = Join-Path $RootDir "backend"
$FrontendDir = $RootDir

function Test-Port {
    param([int]$Port)
    try {
        $tcp = New-Object System.Net.Sockets.TCPClient
        $tcp.Connect("localhost", $Port)
        $tcp.Close()
        return $true
    } catch {
        return $false
    }
}

function Write-Color {
    param([string]$Text, [string]$Color = "White")
    Write-Host $Text -ForegroundColor $Color
}

if ($Action -eq "start") {
    Write-Color "========================================" "Cyan"
    Write-Color "RECIST病灶评估系统 - 一键启动" "Cyan"
    Write-Color "========================================" "Cyan"

    Write-Color ""
    Write-Color "[1/5] 检查Python环境..." "Yellow"
    try {
        $python = Get-Command python -ErrorAction Stop
        Write-Color "✓ Python已安装: $($python.Version)" "Green"
    } catch {
        Write-Color "✗ 未检测到Python，请先安装Python 3.9+" "Red"
        Write-Color "下载地址: https://www.python.org/downloads/" "Gray"
        Read-Host "按Enter键退出"
        exit 1
    }

    Write-Color ""
    Write-Color "[2/5] 检查Node.js环境..." "Yellow"
    try {
        $node = Get-Command node -ErrorAction Stop
        Write-Color "✓ Node.js已安装: $($node.Version)" "Green"
    } catch {
        Write-Color "✗ 未检测到Node.js，请先安装Node.js" "Red"
        Write-Color "下载地址: https://nodejs.org/" "Gray"
        Read-Host "按Enter键退出"
        exit 1
    }

    Write-Color ""
    Write-Color "[3/5] 初始化后端环境..." "Yellow"
    $venvDir = Join-Path $BackendDir "venv"
    if (-not (Test-Path $venvDir)) {
        Write-Color "创建Python虚拟环境..." "Gray"
        python -m venv $venvDir
        Write-Color "✓ 虚拟环境创建成功" "Green"
    } else {
        Write-Color "✓ 虚拟环境已存在" "Green"
    }

    $pip = Join-Path $venvDir "Scripts\pip.exe"
    $requirements = Join-Path $BackendDir "requirements.txt"
    Write-Color "安装Python依赖..." "Gray"
    & $pip install -r $requirements -i https://pypi.tuna.tsinghua.edu.cn/simple --quiet
    Write-Color "✓ Python依赖安装完成" "Green"

    Write-Color ""
    Write-Color "[4/5] 初始化数据库..." "Yellow"
    $pythonScript = Join-Path $BackendDir "scripts\init_db.py"
    $pythonExe = Join-Path $venvDir "Scripts\python.exe"
    & $pythonExe $pythonScript
    Write-Color "✓ 数据库初始化完成" "Green"

    Write-Color ""
    Write-Color "[5/5] 启动服务..." "Yellow"

    if (Test-Port 8080) {
        Write-Color "⚠️ 端口8080已被占用，请先关闭占用该端口的程序" "Yellow"
    }
    if (Test-Port 5173) {
        Write-Color "⚠️ 端口5173已被占用，请先关闭占用该端口的程序" "Yellow"
    }

    Write-Color ""
    Write-Color "启动后端服务 (端口8080)..." "Gray"
    $backendProcess = Start-Process -FilePath $pythonExe -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--reload" -WorkingDirectory $BackendDir -PassThru -NoNewWindow

    Start-Sleep -Seconds 3

    Write-Color "启动前端服务 (端口5173)..." "Gray"
    $frontendProcess = Start-Process -FilePath "npm" -ArgumentList "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173" -WorkingDirectory $FrontendDir -PassThru -NoNewWindow

    Write-Color ""
    Write-Color "========================================" "Cyan"
    Write-Color "服务启动成功！" "Green"
    Write-Color "========================================" "Cyan"
    Write-Color ""
    Write-Color "前端地址: http://localhost:5173" "White"
    Write-Color "后端API: http://localhost:8080" "White"
    Write-Color "API文档: http://localhost:8080/docs" "White"
    Write-Color ""
    Write-Color "默认账号: admin / admin123" "Gray"
    Write-Color ""
    Write-Color "按 Ctrl+C 停止所有服务" "Yellow"

    try {
        while ($true) {
            Start-Sleep -Seconds 1
        }
    } finally {
        Write-Color ""
        Write-Color "正在停止服务..." "Yellow"
        try { $backendProcess.Kill(); Write-Color "✓ 后端服务已停止" "Green" } catch { }
        try { $frontendProcess.Kill(); Write-Color "✓ 前端服务已停止" "Green" } catch { }
        Write-Color "所有服务已停止" "White"
    }

} elseif ($Action -eq "stop") {
    Write-Color "停止所有服务..." "Yellow"
    Get-NetTCPConnection -LocalPort 8080, 5173 -ErrorAction SilentlyContinue | ForEach-Object {
        Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
    }
    Write-Color "✓ 所有服务已停止" "Green"

} elseif ($Action -eq "status") {
    Write-Color "服务状态:" "Cyan"
    Write-Color "后端 (8080): $(if (Test-Port 8080) { "运行中" } else { "已停止" })" "White"
    Write-Color "前端 (5173): $(if (Test-Port 5173) { "运行中" } else { "已停止" })" "White"

} else {
    Write-Color "用法:" "White"
    Write-Color "  .\start_all.ps1 start    # 启动所有服务" "Gray"
    Write-Color "  .\start_all.ps1 stop     # 停止所有服务" "Gray"
    Write-Color "  .\start_all.ps1 status   # 查看服务状态" "Gray"
}