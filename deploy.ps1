<#
.SYNOPSIS
  RECIST 病灶评估系统 — Windows 一键部署脚本
.DESCRIPTION
  1. 检测 Node.js / Python 是否已安装
  2. 缺失则从官方下载并静默安装（需联网；已安装则跳过）
  3. 构建前端 (npm install + npm run build)
  4. 创建 Python 虚拟环境并安装后端依赖
  5. 以生产模式启动服务 (SERVE_FRONTEND=1, DEBUG=False)
  6. 健康检查并输出访问地址
.PARAMETER Port
  服务端口，默认 8080
.PARAMETER SkipBuild
  跳过前端构建（已有 dist 不想重编时使用）
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File deploy.ps1
  powershell -ExecutionPolicy Bypass -File deploy.ps1 -Port 9000
  powershell -ExecutionPolicy Bypass -File deploy.ps1 -SkipBuild
#>
param(
    [int]$Port = 8080,
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"

# 项目根目录（脚本所在目录）
$projectRoot = $PSScriptRoot
if (-not $projectRoot) { $projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition }

# ---------- 工具函数 ----------
function Refresh-Path {
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                [System.Environment]::GetEnvironmentVariable("Path", "User")
}

function Test-CommandExists($cmd) {
    try { Get-Command $cmd -ErrorAction Stop | Out-Null; return $true }
    catch { return $false }
}

function Write-Step($msg) { Write-Host "`n[步骤] $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "[OK] $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "[!] $msg" -ForegroundColor Yellow }

# ---------- 1. 检测 / 安装 Node.js ----------
function Ensure-Node {
    Write-Step "检测 Node.js ..."
    if (Test-CommandExists node) {
        $v = (node -v).TrimStart('v')
        Write-Ok "Node.js 已安装: v$v"
        return
    }
    Write-Host "[*] 未检测到 Node.js，开始下载安装（需联网）..."
    $url = "https://nodejs.org/dist/v20.18.1/node-v20.18.1-x64.msi"
    $msi = Join-Path $env:TEMP "node-install.msi"
    try {
        Invoke-WebRequest -Uri $url -OutFile $msi -UseBasicParsing
        Start-Process msiexec.exe -ArgumentList "/i", "`"$msi`"", "/qn", "/norestart" -Wait
        Refresh-Path
        if (Test-CommandExists node) { Write-Ok "Node.js 安装完成: $(node -v)" }
        else { throw "Node.js 安装后仍未在 PATH 中找到，请手动安装并重启终端" }
    }
    catch {
        Write-Warn "Node.js 自动安装失败：$_"
        Write-Warn "请手动从 https://nodejs.org 下载安装 Node.js 20.x LTS 后重新运行本脚本"
        exit 1
    }
}

# ---------- 2. 检测 / 安装 Python ----------
function Ensure-Python {
    Write-Step "检测 Python ..."
    $pyCmd = $null
    if (Test-CommandExists python) { $pyCmd = "python" }
    elseif (Test-CommandExists py) { $pyCmd = "py" }
    if ($pyCmd) {
        $v = & $pyCmd --version 2>&1
        Write-Ok "Python 已安装: $v"
        return $pyCmd
    }
    Write-Host "[*] 未检测到 Python，开始下载安装（需联网）..."
    $url = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"
    $exe = Join-Path $env:TEMP "python-install.exe"
    try {
        Invoke-WebRequest -Uri $url -OutFile $exe -UseBasicParsing
        Start-Process $exe -ArgumentList "/quiet", "InstallAllUsers=1", "PrependPath=1", "Include_pip=1" -Wait
        Refresh-Path
        if (Test-CommandExists python) { Write-Ok "Python 安装完成: $(python --version 2>&1)" }
        elseif (Test-CommandExists py) { Write-Ok "Python(py) 安装完成" }
        else { throw "Python 安装后仍未在 PATH 中找到，请手动安装并重启终端" }
        return $(if (Test-CommandExists python) { "python" } else { "py" })
    }
    catch {
        Write-Warn "Python 自动安装失败：$_"
        Write-Warn "请手动从 https://www.python.org 下载安装 Python 3.11.x 并勾选 Add to PATH，然后重新运行本脚本"
        exit 1
    }
}

# ---------- 3. 防火墙放行（若以管理员运行） ----------
function Ensure-Firewall {
    $isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
        [Security.Principal.WindowsBuiltInRole]::Administrator)
    if (-not $isAdmin) {
        Write-Warn "当前非管理员，跳过防火墙自动放行。若局域网无法访问，请手动放行端口 $Port"
        return
    }
    try {
        netsh advfirewall firewall add rule name="RECIST_$Port" dir=in action=allow protocol=TCP localport=$Port 2>$null
        Write-Ok "已放行防火墙端口 $Port"
    }
    catch { Write-Warn "防火墙放行失败（可忽略，手动放行即可）" }
}

# ================= 主流程 =================
Write-Host "=============================================" -ForegroundColor Magenta
Write-Host "   RECIST 病灶评估系统 — 一键部署" -ForegroundColor Magenta
Write-Host "   项目目录: $projectRoot" -ForegroundColor Magenta
Write-Host "=============================================" -ForegroundColor Magenta

Ensure-Node
$pyCmd = Ensure-Python
Refresh-Path

# ---------- 4. 前端构建 ----------
if ($SkipBuild) {
    Write-Step "跳过前端构建（使用已有 dist）"
    if (-not (Test-Path (Join-Path $projectRoot "dist"))) {
        Write-Warn "dist 目录不存在，将改为执行构建"
        $SkipBuild = $false
    }
}
if (-not $SkipBuild) {
    Write-Step "安装前端依赖并构建前端 ..."
    Push-Location $projectRoot
    if (-not (Test-Path (Join-Path $projectRoot "node_modules"))) {
        Write-Host "[*] npm install ..."
        npm install
    }
    else { Write-Host "[*] node_modules 已存在，跳过 npm install" }
    Write-Host "[*] npm run build ..."
    npm run build
    Pop-Location
    Write-Ok "前端构建完成"
}

# ---------- 5. 后端虚拟环境与依赖 ----------
$backendDir = Join-Path $projectRoot "backend"
$venv = Join-Path $backendDir "venv"
if (-not (Test-Path $venv)) {
    Write-Step "创建 Python 虚拟环境 ..."
    & $pyCmd -m venv $venv
}
$venvPython = Join-Path $venv "Scripts\python.exe"
$venvPip = Join-Path $venv "Scripts\pip.exe"
Write-Step "安装后端依赖 (requirements.txt) ..."
& $venvPython -m pip install --upgrade pip | Out-Null
& $venvPip install -r (Join-Path $backendDir "requirements.txt")
Write-Ok "后端依赖安装完成"

# ---------- 6. 准备环境变量 ----------
# 优先读取 backend/.env 的 SECRET_KEY；若为默认值则生成随机串（避免每次重启 token 失效需固定值）
$secret = $null
$beEnv = Join-Path $backendDir ".env"
if (Test-Path $beEnv) {
    foreach ($line in (Get-Content $beEnv)) {
        if ($line -match '^\s*SECRET_KEY\s*=\s*(.+)$') {
            $candidate = $Matches[1].Trim().Trim('"').Trim("'")
            if ($candidate -and $candidate -notlike 'your-secret*') { $secret = $candidate }
        }
    }
}
if (-not $secret) {
    $rand = -join ((48..57) + (97..122) | Get-Random -Count 32 | ForEach-Object { [char]$_ })
    $secret = $rand
    Write-Warn "未检测到固定 SECRET_KEY，本次使用随机密钥（服务重启后需重新登录）。建议在生产 backend/.env 中设置固定 SECRET_KEY。"
}

$env:SERVE_FRONTEND = "1"
$env:DEBUG = "False"
$env:PORT = "$Port"
$env:SECRET_KEY = $secret
$env:HOST = "0.0.0.0"

# ---------- 7. 启动服务 ----------
Write-Step "启动服务 (端口 $Port) ..."
$uvicorn = Join-Path $venv "Scripts\uvicorn.exe"
# 新开窗口运行，关闭窗口即停止服务
Start-Process -FilePath $uvicorn `
    -ArgumentList "app.main:app", "--host", "0.0.0.0", "--port", "$Port" `
    -WorkingDirectory $backendDir `
    -WindowStyle Normal

# ---------- 8. 健康检查 ----------
Start-Sleep -Seconds 6
try {
    $resp = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/health" -ErrorAction Stop
    Write-Ok "服务健康检查通过: $($resp | ConvertTo-Json -Compress)"
}
catch {
    Write-Warn "服务健康检查未通过，请查看弹出的后端窗口日志排查问题"
}

Ensure-Firewall

Write-Host "`n=============================================" -ForegroundColor Green
Write-Host "  部署完成！访问地址：" -ForegroundColor Green
Write-Host "  本机:    http://localhost:$Port" -ForegroundColor Green
Write-Host "  局域网:  http://<本机IP>:$Port" -ForegroundColor Green
Write-Host "  API文档: http://localhost:$Port/docs" -ForegroundColor Green
Write-Host "  后端日志窗口已打开，关闭该窗口即停止服务。" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Green
