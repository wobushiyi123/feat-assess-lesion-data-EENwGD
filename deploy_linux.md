# RECIST 病灶评估系统 — Linux 部署手册

> 适用系统：Ubuntu / Debian / CentOS / RHEL / Rocky / AlmaLinux（需 systemd）
> 部署形态：**单进程** FastAPI 同时托管前端 `dist/` + 提供 `/api`，前后端同源一个端口，**无需 Nginx、无需额外数据库服务**
> 数据库：SQLite 单文件（`backend/recist.db`）

---

## 一、把项目传到服务器

推荐**直接拷贝整个项目目录**（最简单，连数据库、`.env` 一起带上）：

```bash
# 在你本机（Windows Git Bash / macOS / Linux 均可）执行
scp -r -P 22 "C:/Users/huawei/.trae-cn/worktrees/wch_code/feat-assess-lesion-data-EENwGD" \
    user@你的服务器IP:/opt/recist
```

> - 想**保留本机已有数据**：连同 `backend/recist.db` 一起传（默认会带）。
> - 想**从空库开始**：传之前删掉 `backend/recist.db`，首次启动会自动建表。
> - 若用 `git clone`：注意 `.gitignore` 忽略了 `dist/`、`.env`、`*.log`，clone 后缺少这些文件，务必先跑 `deploy.sh` 来构建前端、生成 `.env`，否则服务起不来。

---

## 二、在服务器上部署

```bash
ssh user@你的服务器IP
cd /opt/recist
chmod +x deploy.sh

# 默认端口 5173，安装为 systemd 服务并开机自启
sudo ./deploy.sh

# 可选参数：
#   sudo ./deploy.sh --port 9000     # 换端口
#   sudo ./deploy.sh --skip-build    # 已有 dist/，跳过前端构建
#   sudo ./deploy.sh --no-service    # 不装服务，仅前台启动做验证
```

`deploy.sh` 会自动完成：
1. 探测并安装 **Node.js 20 LTS**（构建前端用）
2. 探测并安装 **Python3 + venv + pip**
3. `npm install` + `npm run build` 构建前端到 `dist/`
4. 创建 Python 虚拟环境并安装后端依赖（清华源加速，失败自动回退官方源）
5. 写入生产配置 `backend/.env`：随机生成 `SECRET_KEY`、关闭 `DEBUG`、`SERVE_FRONTEND=True`
6. 注册 **systemd 服务**（崩溃自动重启 + 开机自启），做 `/health` 健康检查
7. 放行防火墙端口（ufw / firewalld 会尝试；云服务器还需在**安全组**放行）

部署完成后脚本会打印访问地址与常用运维命令。

---

## 三、访问与验证

- 本机：`http://127.0.0.1:PORT`
- 局域网/公网：`http://服务器IP:PORT`
- API 文档（Swagger）：`http://服务器IP:PORT/docs`

首次使用：注册一个账号 → 登录 → 在「上传」页导入 EDC 的 Excel → 查看评估。
默认内置账号（建议登录后尽快改密码）：

| 角色 | 账号 | 密码 |
|-----|------|------|
| 管理员 | admin | admin123 |
| 医生 | doctor | doctor123 |

---

## 四、运维命令

```bash
sudo systemctl status recist     # 查看状态
journalctl -u recist -f         # 实时日志
sudo systemctl restart recist    # 重启（改了 backend/.env 后需重启）
sudo systemctl stop recist       # 停止
```

迁移数据库文件（备份/恢复）：`backend/recist.db` 就是整个数据库，停止服务后直接拷贝即可。

---

## 五、重要安全提醒（公网部署必读）

1. **改默认密码**：`admin/admin123`、`doctor/doctor123` 是弱口令，上线前务必改掉。
2. **HTTP 明文**：`deploy.sh` 直接暴露 HTTP，账号密码、JWT 令牌均在明文传输。
   若要在公网使用，**强烈建议**在前面加一层 **Nginx + HTTPS** 反向代理（见下方示例），
   然后让 FastAPI 只监听 `127.0.0.1`、由 Nginx 对外提供 443。
3. **SQLite 并发限制**：多人同时写入可能报 `database is locked`。
   单用户/小团队内网足够；高并发请改用 PostgreSQL（需改数据库连接代码）。
4. **`SECRET_KEY`**：脚本仅在首次（检测到默认占位密钥）时随机生成；重复部署不会覆盖，
   避免已登录用户的 token 失效。如需轮换，手动改 `backend/.env` 后重启服务。

### 可选：Nginx + HTTPS 反代（示例）

```nginx
# /etc/nginx/sites-enabled/recist.conf
server {
    listen 443 ssl;
    server_name your.domain.com;
    ssl_certificate     /path/to/fullchain.pem;
    ssl_certificate_key /path/to/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:5173;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

此时把 `deploy.sh` 的 `--host` 设为 `127.0.0.1`（只监听本机），对外只开 443。

---

## 六、故障排查

| 现象 | 原因 / 解决 |
|------|-------------|
| 访问空白页 | `dist/` 不存在或未构建；确认 `npm run build` 已生成 `dist/index.html` 且 `SERVE_FRONTEND=True` |
| `/health` 不通、服务起不来 | `journalctl -u recist -n 50` 看日志；多为依赖未装或端口被占 |
| 端口被占用 | `sudo lsof -i :5173` 查占用进程，或换 `--port` |
| 登录后不久被踢出 | `SECRET_KEY` 每次随机导致 token 失效；确认 `backend/.env` 里是固定密钥并重启 |
| `database is locked` | SQLite 并发写限制；减少并发写或换 PostgreSQL |
| 外网访问不了 | 云服务器**安全组**未放行该端口（脚本只管服务器本地防火墙，不管云厂商安全组） |
