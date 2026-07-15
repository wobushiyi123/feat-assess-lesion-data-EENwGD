# RECIST 病灶评估系统 — GitHub → Jenkins → 阿里云 → 放行端口 部署手册

> 适用：Vue3 前端 + FastAPI 后端，单进程 `uvicorn` 通过 `SERVE_FRONTEND=1` 同源托管前端 `dist/` 与 `/api`，SQLite 单文件库。
> 拓扑：**Jenkins 与阿里云 ECS 同一台机器**（本机部署，无需跨机 SSH）。
> 访问：**直接 IP:端口 HTTP**（按你确认的方案，未上 HTTPS；上线前务必改默认密码）。

---

## 一、整体架构

```
┌──────────────┐    git push     ┌──────────────┐
│  你本地 / 开发 │ ─────────────▶ │   GitHub 仓库 │
└──────────────┘                 └──────┬───────┘
                                        │ webhook / 轮询
                                        ▼
                              ┌─────────────────────┐
                              │  Jenkins (阿里云ECS) │  端口 9090（管理UI）
                              │  Pipeline 任务       │
                              └──────────┬──────────┘
                                         │ 检出 → rsync → sudo ./deploy.sh
                                         ▼
                              ┌─────────────────────┐
                              │  阿里云 ECS /opt/recist│
                              │  systemd 服务 recist   │  端口 8080（应用）
                              │  单进程托管 前端+API   │
                              └──────────┬──────────┘
                                         │ 需放行
                                         ▼
                              阿里云【安全组】入方向 8080/TCP
                                  ▼
                          浏览器 http://<ECS公网IP>:8080
```

**关键设计点**
- 数据库 `backend/recist.db` 放在持久目录 `/opt/recist`，Jenkins 每次只同步**源码**，rsync 已 `--exclude` 数据库与 venv，升级不会清数据、不需要每次重建环境。
- 端口冲突规避：**应用用 8080**（与 `deploy_linux.md` 一致），**Jenkins 改用 9090**（默认 8080 会冲突）。
- 前端构建、Python 环境、`.env`、systemd、本地防火墙全部由仓库内已有的 `deploy.sh` 完成，Jenkinsfile 只做“检出 + 同步 + 调 deploy.sh + 健康检查”，职责单一、易维护。

---

## 二、前置条件

| 项 | 要求 |
|----|------|
| 阿里云 ECS | 推荐 2 核 4G 起；Ubuntu 20.04/22.04 或 CentOS 7/8/Stream |
| 公网 IP | 已绑定弹性公网 IP |
| GitHub | 你已建好仓库（空仓库即可），拿到 HTTPS 或 SSH 地址 |
| 本地 | 已 `git commit`（本手册第三步会提交好）；能 `git push` 到该仓库 |
| 端口 | 安全组先放行 **9090**（Jenkins，限你办公 IP）与 **8080**（应用，公网） |

---

## 三、GitHub：提交并推送源码

> 仓库根目录已配好 `.gitignore`（排除 `backend/venv`、`*.db`、`*.log`、`.workbuddy/`、`S01001*.xlsx` 等敏感/产物），不会把密钥、数据库、虚拟环境推上去。

在你本地（本工作区）执行：

```bash
# 1) 添加 remote（把 <你的仓库地址> 换成实际 URL，HTTPS 或 SSH 均可）
git remote add origin <你的仓库地址>

# 2) 推送当前分支（若你用 master，把分支名改成 master）
git push -u origin feat-assess-lesion-data-EENwGD
```

- **HTTPS 方式**：密码处填 GitHub **Personal Access Token**（不是账号密码），需有 `repo` 权限。
- **SSH 方式**：先把你本机公钥(`~/.ssh/id_ed25519.pub`)加到 GitHub → SSH keys；且 Jenkins 那边也要能用对应私钥拉取（见第五步凭据）。

> 推送前可用 `git status` / `git ls-files` 确认没有 `venv`、`*.db`、`.workbuddy` 被跟踪。

---

## 四、阿里云 ECS 上安装并配置 Jenkins（端口 9090）

```bash
ssh root@<ECS公网IP>

# ---------- 安装 Java + Jenkins ----------
# Ubuntu / Debian:
sudo apt-get update && sudo apt-get install -y openjdk-17-jdk
sudo curl -fsSL https://pkg.jenkins.io/debian-stable/jenkins.io-2023.key \
  | sudo tee /usr/share/keyrings/jenkins-keyring.asc >/dev/null
echo "deb [signed-by=/usr/share/keyrings/jenkins-keyring.asc] https://pkg.jenkins.io/debian-stable binary/" \
  | sudo tee /etc/apt/sources.list.d/jenkins.list >/dev/null
sudo apt-get update && sudo apt-get install -y jenkins

# CentOS 7（注意用 yum 非 dnf；OpenJDK17 走 Adoptium 更稳）:
# 1) Java 17（Adoptium Temurin 仓库）
sudo bash -c 'cat > /etc/yum.repos.d/adoptium.repo' <<'EOF'
[Adoptium]
name=Adoptium
baseurl=https://packages.adoptium.net/artifactory/rpm/centos/7/$basearch
enabled=1
gpgcheck=1
gpgkey=https://packages.adoptium.net/artifactory/api/gpg/key/public
EOF
sudo yum install -y temurin-17-jdk
# 2) Jenkins
sudo wget -O /etc/yum.repos.d/jenkins.repo https://pkg.jenkins.io/redhat-stable/jenkins.repo
sudo rpm --import https://pkg.jenkins.io/redhat-stable/jenkins.io-2023.key
sudo yum install -y jenkins

# CentOS 8+ / RHEL 8+ / Rocky / Alma:
sudo dnf install -y java-17-openjdk
sudo wget -O /etc/yum.repos.d/jenkins.repo https://pkg.jenkins.io/redhat-stable/jenkins.repo
sudo rpm --import https://pkg.jenkins.io/redhat-stable/jenkins.io-2023.key
sudo dnf install -y jenkins

# ---------- 关键：把 Jenkins 端口改成 9090，避免与应用 8080 冲突 ----------
# Ubuntu（init 脚本）：
sudo sed -i 's/^JENKINS_PORT=.*/JENKINS_PORT=9090/' /etc/default/jenkins 2>/dev/null
# CentOS 7（配置文件 /etc/sysconfig/jenkins）：
sudo sed -i 's/^JENKINS_PORT=.*/JENKINS_PORT="9090"/' /etc/sysconfig/jenkins 2>/dev/null
# CentOS 8+ / RHEL（systemd 单元 Environment）：
if [ -f /usr/lib/systemd/system/jenkins.service ]; then
  sudo sed -i 's/^Environment="JENKINS_PORT=.*/Environment="JENKINS_PORT=9090"/' /usr/lib/systemd/system/jenkins.service
fi
sudo systemctl daemon-reload
sudo systemctl enable --now jenkins

# ---------- 解锁 Jenkins ----------
# 浏览器打开 http://<ECS公网IP>:9090
# 初始管理员密码： sudo cat /var/lib/jenkins/secrets/initialAdminPassword
# 安装“推荐插件”（含 Pipeline、Git），并创建管理员账号。

# ---------- 让 jenkins 用户免密 sudo（deploy.sh 要用 systemctl/ufw/rsync） ----------
echo 'jenkins ALL=(ALL) NOPASSWD: ALL' | sudo tee /etc/sudoers.d/jenkins
sudo chmod 440 /etc/sudoers.d/jenkins

# ---------- 安装 Git（检出代码用） ----------
sudo apt-get install -y git || sudo dnf install -y git
```

### 在 Jenkins 里添加 GitHub 凭据（ID 记为 `github-deploy`）
- 路径：Jenkins →  Manage Jenkins → Credentials → System → Global → Add Credentials
- 仓库为 **私有 + HTTPS**：选 *Username with password*，用户名填 GitHub 账号，密码填 **Personal Access Token**（勾 `repo`）。
- 仓库用 **SSH**：选 *SSH Username with private key*，粘贴能拉取该仓库的私钥（公钥需加在 GitHub）。
- 该凭据在下一步“Pipeline from SCM”里引用。

---

## 五、创建 Jenkins 任务

1. 新建 Item → 名称 `recist-deploy` → 类型 **Pipeline** → OK。
2. **Pipeline 定义** 选 **Pipeline script from SCM**。
3. SCM 选 **Git**：
   - Repository URL：你的 GitHub 仓库地址
   - Credentials：`github-deploy`（上一步建的）
   - Branch：填 `*/feat-assess-lesion-data-EENwGD`（或 `*/master`）
   - Script Path：`Jenkinsfile`
4. **构建触发器**（二选一）：
   - 自动（推荐）：勾 **GitHub hook trigger for GITScm polling**；再到 GitHub 仓库 *Settings → Webhooks → Add*，Payload URL 填 `http://<ECS公网IP>:9090/github-webhook/`，Content type 选 `application/json`。
   - 手动/轮询：勾 **Poll SCM**，Schedule 填 `H/5 * * * *`（每 5 分钟检查一次）。
5. 保存。

---

## 六、首次构建

1. 进入 `recist-deploy` → **立即构建（Build Now）**。
2. Jenkins 会依次：
   - 检出 GitHub 代码到 workspace
   - `rsync` 同步到 `/opt/recist`（保留其中的 `recist.db` 与 `venv`）
   - `sudo ./deploy.sh`：检测/安装 Node20 → `npm install` + `npm run build` → 建 Python venv + 装依赖 → 写 `backend/.env`（首次随机生成 `SECRET_KEY`、`DEBUG=False`、`SERVE_FRONTEND=True`）→ 注册并启动 systemd 服务 `recist` → 放行本地防火墙 8080
   - `curl /health` 健康检查
3. 控制台出现 **`部署成功 ✓ 公网访问: http://<ECS公网IP>:8080`** 即成功。

> 若 ECS 之前没装 Node，首次 `deploy.sh` 会用 `apt/dnf` 装 Node20（需联网），耗时稍长属正常。

---

## 七、放行端口（阿里云安全组 + 防火墙）

**1) 阿里云安全组（控制台，必做——这是“放行端口”的核心）**
- 阿里云控制台 → **云服务器 ECS** → 实例 → **安全组** → 配置规则 → **入方向** → 添加规则：
  | 规则 | 协议 | 端口范围 | 授权对象 | 说明 |
  |------|------|----------|----------|------|
  | 应用 | TCP | `8080/8080` | `0.0.0.0/0`（公网）或限你 IP | 对外提供 RECIST 服务 |
  | 管理 | TCP | `9090/9090` | `<你办公IP>/32` | Jenkins 仅自己访问，切勿对公网开放 |
- 出方向一般默认全通，无需改。

**2) ECS 本地防火墙（deploy.sh 已尽力放行；按需确认）**
- Ubuntu（ufw）：`sudo ufw status` 看是否 active；未 active 可不理（安全组已生效）。
- CentOS（firewalld）：`sudo firewall-cmd --list-ports` 确认 `8080/tcp` 在列；不在则 `sudo firewall-cmd --permanent --add-port=8080/tcp && sudo firewall-cmd --reload`。

**3) 验证访问**
- 浏览器打开 `http://<ECS公网IP>:8080` → 应看到登录页。
- API 文档：`http://<ECS公网IP>:8080/docs`。

---

## 八、上线前必做（安全）

1. **改默认密码**：登录后把 `admin/admin123`、`doctor/doctor123` 改为强口令。
2. **限制 Jenkins 暴露面**：9090 只对你的办公 IP 开放（安全组已配）；条件允许建议再加一层 Nginx 反向代理 + 基础认证。
3. **HTTP 明文风险**：当前直接 IP:端口是明文，账号/JWT 裸传。公网长期使用强烈建议加 Nginx + HTTPS（见 `deploy_linux.md` 第五节示例），让 FastAPI 只监听 `127.0.0.1`、`PORT=8080`，对外只开 443。
4. **SQLite 并发**：小团队内网足够；多人高频并发写入可能 `database is locked`，必要时换 PostgreSQL（需改连接代码）。

---

## 九、日常更新 / 回滚

- **发新版**：本地改代码 → `git commit` → `git push` → Jenkins 自动/手动构建 → ECS 自动更新并重启服务。
- **不丢数据**：数据库在 `/opt/recist/backend/recist.db`，每次只同步源码，升级不被覆盖。
- **回滚**：
  - 简单：`git revert <问题提交>` 后重新 push，或 Jenkins 任务左侧 *Build History* 选旧构建 *Rebuild*。
  - 数据回滚：停止服务 `sudo systemctl stop recist`，用备份的 `recist.db` 覆盖，再 `sudo systemctl start recist`。

## 十、常用运维命令（ECS 上）

```bash
sudo systemctl status recist      # 查看状态
journalctl -u recist -f           # 实时日志
sudo systemctl restart recist     # 重启（改了 backend/.env 后需重启）
sudo systemctl stop recist        # 停止
# 触发一次重新部署：Jenkins → recist-deploy → 立即构建
```
