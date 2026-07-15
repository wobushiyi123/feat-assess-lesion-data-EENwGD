#!/usr/bin/env bash
# =============================================================================
# RECIST 病灶评估系统 — Linux 一键部署脚本
# 适用：Ubuntu / Debian / CentOS / RHEL / Rocky / AlmaLinux (systemd)
# 形态：单进程 FastAPI 同时托管前端 dist + 提供 /api，同源一个端口，无需 Nginx
# 数据库：SQLite 单文件 (backend/recist.db)，无需额外数据库服务
# 用法：
#   chmod +x deploy.sh
#   sudo ./deploy.sh                 # 默认端口 8080，安装为 systemd 服务并开机自启
#   sudo ./deploy.sh --port 9000     # 指定端口
#   sudo ./deploy.sh --skip-build    # 已有 dist，跳过前端构建
#   sudo ./deploy.sh --no-service    # 不装 systemd，仅前台启动一次做验证
# =============================================================================
set -euo pipefail

# ---------- 可配置项（命令行参数会覆盖） ----------
PORT=8080
HOST="0.0.0.0"
SERVICE_NAME="recist"
SKIP_BUILD=0
INSTALL_SERVICE=1

# ---------- 解析参数 ----------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --port)       PORT="$2"; shift 2 ;;
    --host)       HOST="$2"; shift 2 ;;
    --name)       SERVICE_NAME="$2"; shift 2 ;;
    --skip-build) SKIP_BUILD=1; shift ;;
    --no-service) INSTALL_SERVICE=0; shift ;;
    -h|--help)
      grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "未知参数: $1"; exit 1 ;;
  esac
done

# ---------- 路径与运行用户 ----------
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
VENV_DIR="$BACKEND_DIR/venv"
# 以谁的身份运行服务：优先用调用 sudo 的原始用户，避免服务以 root 常驻
RUN_USER="${SUDO_USER:-$(id -un)}"

log()  { printf '\033[1;32m[部署]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[警告]\033[0m %s\n' "$*"; }
err()  { printf '\033[1;31m[错误]\033[0m %s\n' "$*" >&2; }

log "项目根目录: $ROOT_DIR"
log "运行用户   : $RUN_USER"
log "监听地址   : $HOST:$PORT"

# ---------- 包管理器探测 ----------
if command -v apt-get >/dev/null 2>&1; then
  PKG="apt"
elif command -v dnf >/dev/null 2>&1; then
  PKG="dnf"
elif command -v yum >/dev/null 2>&1; then
  PKG="yum"
else
  PKG="unknown"
fi
log "包管理器   : $PKG"

SUDO=""
if [[ "$(id -u)" -ne 0 ]]; then
  if command -v sudo >/dev/null 2>&1; then SUDO="sudo"; else
    warn "非 root 且无 sudo，安装系统依赖/配置服务可能失败，建议用 root 运行"
  fi
fi

pkg_install() {
  case "$PKG" in
    apt) $SUDO apt-get update -y && $SUDO apt-get install -y "$@" ;;
    dnf) $SUDO dnf install -y "$@" ;;
    yum) $SUDO yum install -y "$@" ;;
    *)   warn "无法自动安装 $*，请手动安装后重试" ;;
  esac
}

# =============================================================================
# 1) Node.js (>=18) —— 仅在前端需要本地构建时（SKIP_BUILD=0）才安装
#    注意：CentOS/RHEL 7 的 glibc 仅 2.17，无法运行 Node 18+，故生产部署
#    统一使用仓库内预编译的 dist/（--skip-build），不在服务器上安装 Node。
# =============================================================================
if [[ "$SKIP_BUILD" -eq 0 ]]; then
  need_node=1
  if command -v node >/dev/null 2>&1; then
    NODE_MAJOR="$(node -v | sed 's/^v//' | cut -d. -f1)"
    if [[ "$NODE_MAJOR" -ge 18 ]]; then need_node=0; log "已检测到 Node $(node -v)"; fi
  fi
  if [[ "$need_node" -eq 1 ]]; then
    log "安装 Node.js 20 LTS ..."
    case "$PKG" in
      apt)
        curl -fsSL https://deb.nodesource.com/setup_20.x | $SUDO -E bash -
        pkg_install nodejs ;;
      dnf|yum)
        curl -fsSL https://rpm.nodesource.com/setup_20.x | $SUDO -E bash -
        pkg_install nodejs ;;
      *) err "请手动安装 Node.js >= 18 后重试"; exit 1 ;;
    esac
    log "Node 安装完成: $(node -v)"
  fi
else
  log "跳过前端构建（--skip-build）：使用仓库内预编译 dist/，无需 Node.js"
fi

# =============================================================================
# 2) Python3 + venv + pip
#    CentOS/RHEL 7 自带 python3 仅 3.6，不满足 FastAPI(Python>=3.8)。
#    通过 Software Collections(rh-python311) 提供 Python 3.11；
#    Ubuntu/Debian 用系统 python3(>=3.8)。
# =============================================================================
if [[ "$PKG" == "yum" || "$PKG" == "dnf" ]]; then
  if ! command -v python3.11 >/dev/null 2>&1; then
    log "安装 RHSCL Python 3.11（CentOS/RHEL 默认 python3 过旧，无法满足 FastAPI）..."
    pkg_install centos-release-scl
    pkg_install rh-python311
  fi
  # 仅当前 shell 启用（后续 venv/依赖均用 3.11）；服务运行时用 venv 绝对路径，不依赖 SCL
  source /opt/rh/rh-python311/enable 2>/dev/null || true
fi
if ! command -v python3 >/dev/null 2>&1; then
  log "安装 Python3 ..."
  case "$PKG" in
    apt) pkg_install python3 python3-venv python3-pip ;;
    dnf|yum) pkg_install python3 python3-pip ;;
  esac
fi
# Debian/Ubuntu 的 venv 常需单独包
if [[ "$PKG" == "apt" ]]; then
  python3 -m venv --help >/dev/null 2>&1 || pkg_install python3-venv
fi
log "已检测到 $(python3 --version)"
command -v curl >/dev/null 2>&1 || pkg_install curl

# =============================================================================
# 3) 构建前端 -> dist/
# =============================================================================
if [[ "$SKIP_BUILD" -eq 1 ]]; then
  if [[ -f "$ROOT_DIR/dist/index.html" ]]; then
    log "跳过前端构建，复用现有 dist/"
  else
    warn "--skip-build 但 dist/index.html 不存在，将强制构建"
    SKIP_BUILD=0
  fi
fi
if [[ "$SKIP_BUILD" -eq 0 ]]; then
  log "安装前端依赖并构建 (npm install && npm run build) ..."
  cd "$ROOT_DIR"
  npm install
  npm run build
  [[ -f "$ROOT_DIR/dist/index.html" ]] || { err "构建后仍无 dist/index.html，请检查"; exit 1; }
  log "前端构建完成: $ROOT_DIR/dist"
fi

# =============================================================================
# 4) 后端虚拟环境 + 依赖
# =============================================================================
log "创建/更新 Python 虚拟环境 ..."
cd "$BACKEND_DIR"
[[ -d "$VENV_DIR" ]] || python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --upgrade pip
# 国内源加速；失败自动回退官方源
"$VENV_DIR/bin/pip" install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple \
  || "$VENV_DIR/bin/pip" install -r requirements.txt
log "后端依赖安装完成"

# =============================================================================
# 5) 生产环境配置 backend/.env（生成随机 SECRET_KEY、关闭 DEBUG）
# =============================================================================
ENV_FILE="$BACKEND_DIR/.env"
touch "$ENV_FILE"
set_env() {  # set_env KEY VALUE —— 有则替换，无则追加
  local key="$1" val="$2"
  if grep -qE "^${key}=" "$ENV_FILE"; then
    sed -i "s|^${key}=.*|${key}=${val}|" "$ENV_FILE"
  else
    printf '%s=%s\n' "$key" "$val" >> "$ENV_FILE"
  fi
}
# 仅当仍是默认/占位密钥时才生成新随机密钥，避免每次部署导致已登录用户 token 失效
if ! grep -qE '^SECRET_KEY=' "$ENV_FILE" || grep -qE '^SECRET_KEY=(your-secret-key-here-change-in-production)?\s*$' "$ENV_FILE"; then
  NEW_SECRET="$(python3 -c 'import secrets;print(secrets.token_urlsafe(48))')"
  set_env SECRET_KEY "$NEW_SECRET"
  log "已生成随机 SECRET_KEY"
fi
set_env DEBUG "False"
set_env HOST "$HOST"
set_env PORT "$PORT"
set_env SERVE_FRONTEND "True"
log "已更新生产配置: $ENV_FILE (DEBUG=False, SERVE_FRONTEND=True, PORT=$PORT)"

# =============================================================================
# 5.5) 初始化数据库（建默认账号 admin/doctor + 演示受试者，幂等：已存在则跳过）
#      首次部署时 recist.db 尚不存在，此步骤确保建好表+账号，使系统可直接登录。
# =============================================================================
log "初始化数据库（建默认账号，已存在则跳过）..."
cd "$BACKEND_DIR"
"$VENV_DIR/bin/python" -m scripts.init_db \
  || warn "数据库初始化脚本返回非零（可忽略：服务首次启动会自动建表，但默认账号需手动补建：sudo -u $RUN_USER $VENV_DIR/bin/python -m scripts.init_db）"


# =============================================================================
# 6) 安装 systemd 服务（开机自启 + 崩溃自动重启）或前台验证
# =============================================================================
UVICORN="$VENV_DIR/bin/python -m uvicorn app.main:app --host $HOST --port $PORT"

if [[ "$INSTALL_SERVICE" -eq 1 ]]; then
  UNIT="/etc/systemd/system/${SERVICE_NAME}.service"
  log "写入 systemd 服务: $UNIT"
  $SUDO bash -c "cat > '$UNIT'" <<EOF
[Unit]
Description=RECIST Assessment System (FastAPI single-process, serves frontend + API)
After=network.target

[Service]
Type=simple
User=$RUN_USER
WorkingDirectory=$BACKEND_DIR
Environment=SERVE_FRONTEND=1
Environment=DEBUG=False
Environment=HOST=$HOST
Environment=PORT=$PORT
ExecStart=$UVICORN
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

  $SUDO systemctl daemon-reload
  $SUDO systemctl enable "$SERVICE_NAME"
  $SUDO systemctl restart "$SERVICE_NAME"
  log "服务已启动并设为开机自启 (systemctl status $SERVICE_NAME)"

  # 健康检查
  sleep 3
  if curl -fsS "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then
    log "健康检查通过 ✓"
  else
    warn "健康检查未通过，查看日志: journalctl -u $SERVICE_NAME -n 50 --no-pager"
  fi
else
  log "前台启动验证（Ctrl+C 停止）..."
  cd "$BACKEND_DIR"
  SERVE_FRONTEND=1 DEBUG=False $UVICORN &
  APP_PID=$!
  sleep 4
  if curl -fsS "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then
    log "健康检查通过 ✓ (PID=$APP_PID)"
  else
    warn "健康检查未通过，请检查上方日志"
  fi
  wait "$APP_PID"
fi

# =============================================================================
# 7) 防火墙放行（尽力而为）
# =============================================================================
if command -v ufw >/dev/null 2>&1 && $SUDO ufw status 2>/dev/null | grep -qi active; then
  $SUDO ufw allow "${PORT}/tcp" || true
  log "ufw 已放行 ${PORT}/tcp"
elif command -v firewall-cmd >/dev/null 2>&1 && $SUDO firewall-cmd --state >/dev/null 2>&1; then
  $SUDO firewall-cmd --permanent --add-port="${PORT}/tcp" || true
  $SUDO firewall-cmd --reload || true
  log "firewalld 已放行 ${PORT}/tcp"
else
  warn "未检测到活动的 ufw/firewalld，如云服务器请在【安全组】放行 ${PORT} 端口"
fi

IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
echo
log "========================================================"
log " 部署完成！访问地址："
log "   本机 : http://127.0.0.1:$PORT"
[[ -n "${IP:-}" ]] && log "   局域网/公网 : http://$IP:$PORT   (公网需另在安全组放行)"
log "   API 文档 : http://$IP:$PORT/docs"
log "--------------------------------------------------------"
log " 服务管理："
log "   状态 : sudo systemctl status $SERVICE_NAME"
log "   日志 : journalctl -u $SERVICE_NAME -f"
log "   重启 : sudo systemctl restart $SERVICE_NAME"
log "   停止 : sudo systemctl stop $SERVICE_NAME"
log "========================================================"
