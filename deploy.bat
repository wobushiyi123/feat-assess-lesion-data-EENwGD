@echo off
chcp 65001 >nul
echo 正在启动 RECIST 病灶评估系统一键部署...
echo (建议以管理员身份运行，以便自动放行防火墙)
echo.
powershell -ExecutionPolicy Bypass -File "%~dp0deploy.ps1" %*
pause
