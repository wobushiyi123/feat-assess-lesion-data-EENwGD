#!/usr/bin/env bash
# =============================================================================
# RECIST 病灶评估系统 — Linux 一键部署脚本
# 适用：Ubuntu / Debian / CentOS / RHEL / Rocky / AlmaLinux (systemd)
# 形态：单进程 FastAPI 同时托管前端 dist + 提供 /api，同源一个端口，无需 Nginx
# 数据库：SQLite 单文件 (backend/recist.db)，无需额外数据库服务
# 用法：
#   chmod +x deploy.sh
#   sudo ./deploy.sh                 # 默认端口 5173，安装为 systemd 服务并开机自启
#   sudo ./deploy.sh --port 9000     # 指定端口
#   sudo ./deploy.sh --skip-build    # 已有 dist，跳过前端构建
#   sudo ./deploy.sh --no-service    # 不装 systemd，仅前台启动一次做验证
# =============================================================================
set -euo pipefail

# ---------- 可配置项（命令行参数会覆盖） ----------
PORT=5173
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

# 修复 CentOS/RHEL 7 EOL 后 base 仓库失效：重指向官方归档源 vault.centos.org
fix_centos_base_repo() {
  [[ -f /etc/yum.repos.d/CentOS-Base.repo ]] || return 0
  $SUDO tee /etc/yum.repos.d/CentOS-Base.repo >/dev/null <<EOF
[base]
name=CentOS-7 - Base (vault)
baseurl=https://vault.centos.org/centos/7/os/\$basearch/
gpgcheck=0
enabled=1

[updates]
name=CentOS-7 - Updates (vault)
baseurl=https://vault.centos.org/centos/7/updates/\$basearch/
gpgcheck=0
enabled=1

[extras]
name=CentOS-7 - Extras (vault)
baseurl=https://vault.centos.org/centos/7/extras/\$basearch/
gpgcheck=0
enabled=1
EOF
  log "已把 CentOS base/updates/extras 仓库重指向 vault.centos.org（CentOS 7 EOL 归档源）"
}

# 确保 C/C++ 编译工具链存在（源码构建 greenlet/uvloop/httptools 等扩展需要）
ensure_c_toolchain() {
  if command -v gcc >/dev/null 2>&1 && command -v g++ >/dev/null 2>&1 && command -v make >/dev/null 2>&1; then
    log "已检测到 C/C++ 工具链: gcc $(gcc -dumpversion)"
    return 0
  fi
  log "安装 C/C++ 编译工具链 (gcc/g++/make) ..."
  case "$PKG" in
    apt) pkg_install build-essential ;;
    dnf|yum)
      fix_centos_base_repo
      pkg_install gcc gcc-c++ make ;;
    *) warn "未检测到 C/C++ 编译器，请手动安装 gcc/g++/make 后重试" ;;
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
# 2) Python3 (>=3.8) + venv + pip
#    策略：优先用系统 python3（>=3.8，Ubuntu22.04/AlmaLinux9 均满足）；
#    若系统 python3 过旧（CentOS/RHEL 7 自带仅 3.6）或缺失，则下载
#    python-build-standalone —— GitHub 上预编译的独立 Python 3.11，
#    兼容 CentOS7 的 glibc 2.17，解压即用，完全不依赖 yum/SCL 归档源
#    （CentOS7 EOL 后 SCL rh-python311 已无法从任何官方源安装）。
# =============================================================================
command -v curl >/dev/null 2>&1 || pkg_install curl

PYTHON_BIN=""
pick_python() {  # 选出一个 >=3.8 的解释器写入全局 PYTHON_BIN
  local cand
  for cand in python3.12 python3.11 python3.10 python3.9 python3.8 python3; do
    if command -v "$cand" >/dev/null 2>&1 \
       && "$cand" -c 'import sys;raise SystemExit(0 if sys.version_info[:2]>=(3,8) else 1)' 2>/dev/null; then
      PYTHON_BIN="$(command -v "$cand")"; return 0
    fi
  done
  return 1
}

# Debian/Ubuntu：系统 python3 一般已够新，仅补 venv/pip 包
if [[ "$PKG" == "apt" ]]; then
  pick_python || pkg_install python3 python3-venv python3-pip
fi

if ! pick_python; then
  # 系统无 >=3.8 的 python（典型：CentOS7 自带 3.6）→ 下载 python-build-standalone
  PBS_DIR=/opt/python311
  if [[ ! -x "$PBS_DIR/bin/python3.11" ]]; then
    log "系统 python3 过旧/缺失，下载 python-build-standalone Python 3.11（免 yum/SCL，兼容 CentOS7 glibc2.17）..."
    arch="$(uname -m)"
    case "$arch" in
      x86_64|amd64)   PBS_ARCH="x86_64" ;;
      aarch64|arm64)  PBS_ARCH="aarch64" ;;
      *) err "不支持的架构: $arch（python-build-standalone 仅提供 x86_64/aarch64）"; exit 1 ;;
    esac
    PBS_VER="3.11.9"; PBS_TAG="20240814"
    ASSET="cpython-${PBS_VER}+${PBS_TAG}-${PBS_ARCH}-unknown-linux-gnu-install_only.tar.gz"
    TARBALL="/tmp/py311-standalone.tar.gz"
    dl_ok=0
    for url in \
      "https://github.com/astral-sh/python-build-standalone/releases/download/${PBS_TAG}/${ASSET}" \
      "https://ghproxy.net/https://github.com/astral-sh/python-build-standalone/releases/download/${PBS_TAG}/${ASSET}" \
      "https://github.com/indygreg/python-build-standalone/releases/download/${PBS_TAG}/${ASSET}" \
      "https://gh-proxy.com/https://github.com/astral-sh/python-build-standalone/releases/download/${PBS_TAG}/${ASSET}" ; do
      log "尝试下载: $url"
      if curl -fSL --retry 3 --connect-timeout 20 -o "$TARBALL" "$url"; then dl_ok=1; break; fi
      warn "下载失败，尝试下一个镜像..."
    done
    [[ "$dl_ok" -eq 1 ]] || { err "python-build-standalone 下载失败（ECS 无法访问 GitHub/镜像）。可手动下载 $ASSET 传到 $TARBALL 后重跑，或改用 AlmaLinux9/Ubuntu22.04"; exit 1; }
    # install_only tarball 解压出顶层目录 python/，移动到 PBS_DIR
    $SUDO rm -rf /tmp/python "$PBS_DIR"
    $SUDO tar -xzf "$TARBALL" -C /tmp
    $SUDO mkdir -p "$(dirname "$PBS_DIR")"
    $SUDO mv /tmp/python "$PBS_DIR"
    rm -f "$TARBALL"
    log "python-build-standalone 安装完成: $($PBS_DIR/bin/python3.11 --version)"
  fi
  export PATH="$PBS_DIR/bin:$PATH"
  PYTHON_BIN="$PBS_DIR/bin/python3.11"
fi

log "使用 Python: $("$PYTHON_BIN" --version) ($PYTHON_BIN)"

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
[[ -d "$VENV_DIR" ]] || "$PYTHON_BIN" -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --upgrade pip wheel setuptools
# 源码构建（greenlet/uvloop/httptools 等 C 扩展）需要 C/C++ 编译器；
# python-build-standalone 的 sysconfig 默认用 clang，ECS 上通常只有 gcc，
# 故先确保 gcc/g++/make 已装（CentOS7 的 base 仓库已 EOL，会自动重指向 vault），
# 再用 CC/CXX 强制走 gcc，避免缺 clang 导致构建失败。
ensure_c_toolchain
# 国内源加速；失败自动回退官方源；--prefer-binary 优先用预编译 wheel，缺则源码构建
CC=gcc CXX=g++ "$VENV_DIR/bin/pip" install -r requirements.txt --prefer-binary \
  -i https://pypi.tuna.tsinghua.edu.cn/simple \
  || CC=gcc CXX=g++ "$VENV_DIR/bin/pip" install -r requirements.txt --prefer-binary
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
  NEW_SECRET="$("$VENV_DIR/bin/python" -c 'import secrets;print(secrets.token_urlsafe(48))')"
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
  # 关键：部署全程以 root(sudo) 运行，但 systemd 服务以 $RUN_USER(jenkins) 身份运行。
  # 若不修正属主，$RUN_USER 将无法写入 SQLite 数据库 → 登录可过（只读），导入/写操作 500。
  $SUDO chown -R "$RUN_USER:$RUN_USER" /opt/recist/
  log "已将 /opt/recist/ 属主修正为 $RUN_USER（服务运行用户）"
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
