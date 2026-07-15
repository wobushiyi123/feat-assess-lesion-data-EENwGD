# RECIST 病灶评估系统 — Windows 部署环境配置手册

> 适用系统：Windows 10 / 11 / Windows Server 2016+
> 部署形态：单进程同时托管前端 + 后端（同源一个端口，无需 Nginx）
> 数据库：SQLite 单文件（无需额外安装数据库服务）

---

## 一、环境依赖总览

| 组件 | 最低版本 | 推荐版本 | 用途 | 是否必须 | 官方下载 |
|------|----------|----------|------|----------|----------|
| **Node.js**（含 npm） | 18.x | **20.x LTS** | 构建前端（Vite） | 是 | https://nodejs.org |
| **Python** | 3.9 | **3.10 / 3.11** | 运行后端（FastAPI） | 是 | https://www.python.org |
| pip（随 Python） | — | — | Python 包管理 | 是（随 Python） | 随 Python 安装 |
| SQLite | 内置 | — | 数据库（单文件） | 否（已内置） | 无需安装 |
| Git | 任意 | 最新 | 拉取项目代码（可选） | 否 | https://git-scm.com |

> ⚠️ 为什么推荐 Python 3.11：本项目依赖 `passlib[bcrypt]`，在 3.11 下有预编译 wheel，安装最稳；3.12+ 在个别环境需要本地编译。

---

## 二、逐项安装与配置（Windows）

### 2.1 Node.js

- **下载地址**：https://nodejs.org/en/download/ → 选择 **Windows Installer (.msi) 64-bit**
- **直链示例**（LTS）：`https://nodejs.org/dist/v20.18.1/node-v20.18.1-x64.msi`
- **安装步骤**：
  1. 双击 `.msi`，一路 Next
  2. 确认勾选 **「Add to PATH」**（默认已勾选）
  3. 完成安装
- **安装路径**：默认 `C:\Program Files\nodejs\`；npm 全局模块在 `C:\Users\<你的用户名>\AppData\Roaming\npm`
- **验证**（PowerShell / CMD）：
  ```bat
  node -v
  npm -v
  ```

### 2.2 Python

- **下载地址**：https://www.python.org/downloads/windows/ → 选择 **Python 3.11.x Windows installer (64-bit)**
- **直链示例**：`https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe`
- **安装步骤**：
  1. 双击 `.exe`
  2. **务必勾选「Add python.exe to PATH」**
  3. 点击 **「Customize installation」** → 确认 **pip** 已勾选
  4. 在 Advanced 选项中勾选 **「Install for all users」** 与 **「Add Python to environment variables」**
  5. Install
- **安装路径**：`C:\Python311\`（All users）或 `C:\Users\<用户名>\AppData\Local\Programs\Python\Python311\`
- **验证**：
  ```bat
  python --version
  pip --version
  ```

### 2.3 数据库（SQLite，无需安装）

系统使用 SQLAlchemy 直接管理单个 SQLite 文件，**无需安装任何数据库服务**。

- **数据库文件位置**：`<项目根目录>\backend\recist.db`
- **首次启动**后端时 `Base.metadata.create_all` 会自动建表
- **清零数据**：停止服务后直接删除 `backend\recist.db` 文件，重启即得到空库
- ⚠️ SQLite 为文件锁，并发写入能力有限，**适合单用户 / 小团队内网使用**；高并发请改用 PostgreSQL（需改代码）

### 2.4 Git（可选）

仅在需要从代码仓库拉取项目时安装：https://git-scm.com/download/win

---

## 三、项目目录结构与关键配置

```
<项目根>/
├─ .env                      # 前端配置（VITE_API_URL，部署留空=同源）
├─ package.json              # 前端依赖与构建脚本
├─ vite.config.js            # 开发代理（仅本地开发用，部署无关）
├─ dist/                     # 前端构建产物（部署时由 npm run build 生成）
├─ src/                      # 前端源码
├─ backend/
│  ├─ .env                   # 后端配置（端口/密钥/调试/生产托管开关）
│  ├─ requirements.txt       # 后端 Python 依赖清单
│  ├─ recist.db              # SQLite 数据库文件（运行时生成，不在 git 中）
│  └─ app/
│     ├─ main.py             # 应用入口；含 SERVE_FRONTEND 静态托管开关
│     └─ core/config.py      # 配置（读 backend/.env）
├─ deploy.ps1                # 一键部署脚本（PowerShell）
└─ deploy.bat                # 双击入口（调用 deploy.ps1）
```

### 关键配置说明

#### 1. 前端 `.env`（项目根）
| 配置项 | 说明 | 部署建议 |
|--------|------|----------|
| `VITE_API_URL` | 前端调用的 API 基址 | **留空**（同源，前端与后端同一端口） |

#### 2. 后端 `backend/.env`
| 配置项 | 说明 | 部署建议 |
|--------|------|----------|
| `APP_NAME` | 应用名 | 可保留 |
| `DEBUG` | 调试模式（开启会输出 SQL） | **生产设 `False`** |
| `HOST` | 监听地址 | `0.0.0.0`（允许局域网访问） |
| `PORT` | 监听端口 | 如 `8080` |
| `SECRET_KEY` | JWT 签名密钥 | **生产必须改为一长串随机字符串** |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 登录有效期（分钟） | 默认 1440（1 天） |
| `CORS_ORIGINS` | 允许跨域的前端域名 | 单端口同源可留默认 |
| `SERVE_FRONTEND` | 是否由后端托管前端静态文件 | **生产设 `True`**（单进程部署关键） |

> 修改 `backend/.env` 后需**重启后端服务**生效。环境变量优先级高于 `.env` 文件。

#### 3. 数据库文件路径
由 `backend/app/core/database.py` 决定：`BASE_DIR/recist.db`，即 `backend\recist.db`。

#### 4. 前端构建配置 `vite.config.js`
`base` 默认 `/`，前端部署在域名根路径即可（如 `http://ip:8080/`）。若需部署到子路径（如 `/recist/`），需在此设置 `base: '/recist/'` 并相应调整。

---

## 四、部署方式

### 4.1 一键部署（推荐）

将整个项目拷贝到服务器后，在**项目根目录**双击 `deploy.bat`（或右键 `deploy.ps1` 用 PowerShell 运行，建议 **「以管理员身份运行」** 以便自动放行防火墙）。

脚本会自动完成：
1. 检测 Node.js / Python 是否已安装
2. 缺失则从官方下载并静默安装（联网）
3. `npm install` + `npm run build` 构建前端
4. 创建 Python 虚拟环境并安装后端依赖
5. 以生产模式（`SERVE_FRONTEND=1`、`DEBUG=False`）启动服务
6. 健康检查并输出访问地址

可加参数：
```powershell
# 指定端口（默认 8080）
powershell -ExecutionPolicy Bypass -File deploy.ps1 -Port 9000
# 跳过前端构建（已有 dist 不想重编时）
powershell -ExecutionPolicy Bypass -File deploy.ps1 -SkipBuild
```

### 4.2 手动部署

```bat
:: 1) 构建前端
cd <项目根>
npm install
npm run build

:: 2) 后端虚拟环境 + 依赖
cd backend
python -m venv venv
venv\Scripts\pip install -r requirements.txt

:: 3) 启动（生产模式）
set SERVE_FRONTEND=1
set DEBUG=False
set PORT=8080
venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8080
```

---

## 五、启动与访问

- 本机访问：http://localhost:8080
- 局域网访问：http://<服务器IP>:8080
- API 文档（Swagger）：http://<服务器IP>:8080/docs
- 首次使用：进入系统注册一个账号 → 登录 → 在「上传」页导入 EDC 的 Excel → 查看评估

---

## 六、端口与防火墙

若局域网其他机器无法访问，需在服务器放行端口（以 8080 为例，管理员 CMD/PowerShell）：

```bat
netsh advfirewall firewall add rule name="RECIST" dir=in action=allow protocol=TCP localport=8080
```

或用 PowerShell：
```powershell
New-NetFirewallRule -DisplayName "RECIST" -Direction Inbound -Protocol TCP -LocalPort 8080 -Action Allow
```

---

## 七、设为开机自启（可选）

`deploy.ps1` 启动的是前台窗口（关闭窗口即停止）。若需作为后台服务常驻，可用 **NSSM**（Non-Sucking Service Manager）：

1. 下载 NSSM：https://nssm.cc
2. 命令行：
   ```bat
   nssm install RECIST "C:\<项目根>\backend\venv\Scripts\python.exe"
   nssm set RECIST AppParameters "-m uvicorn app.main:app --host 0.0.0.0 --port 8080"
   nssm set RECIST AppDirectory "C:\<项目根>\backend"
   nssm set RECIST AppEnvironmentExtra "SERVE_FRONTEND=1" "DEBUG=False"
   nssm start RECIST
   ```

---

## 八、常见问题

| 现象 | 原因 / 解决 |
|------|-------------|
| 访问显示空白 | 前端未构建或 `SERVE_FRONTEND` 未开启；确认 `dist/` 存在且后端以生产模式启动 |
| 端口被占用 | 换端口（`-Port` 参数或 `backend/.env` 的 `PORT`）；或释放占用进程 |
| 登录后不久被退出 | `SECRET_KEY` 每次随机导致 token 失效；在 `backend/.env` 设置固定 `SECRET_KEY` |
| 并发写入报错 `database is locked` | SQLite 限制；改用 PostgreSQL 或避免多人同时写 |
| `npm` / `python` 命令找不到 | 未加入 PATH；重装并勾选 Add to PATH，或重启终端 |
| 下载安装卡住 | 服务器无外网；改用离线安装（手动装好 Node/Python 后跑脚本，脚本会跳过已安装项） |
