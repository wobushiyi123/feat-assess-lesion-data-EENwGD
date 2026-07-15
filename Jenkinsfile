// =============================================================================
// RECIST 病灶评估系统 — Jenkins Pipeline
// 部署拓扑：Jenkins 与阿里云 ECS 同一台机器（本机部署）
//   1) 从 GitHub 检出代码到 Jenkins workspace
//   2) rsync 同步到 /opt/recist（保留目标机的数据库与 venv，避免每次重建）
//   3) sudo ./deploy.sh 完成：装 Node → 构建前端 → 建 venv → 写 .env → 注册 systemd → 放行本地防火墙
//   4) 健康检查 /health
//
// 配置说明：
//   - 该 Job 请选择 “Pipeline script from SCM”，SCM 指向本 GitHub 仓库，
//     Branch 填你的分支（如 feat-assess-lesion-data-EENwGD 或 master），
//     Script Path 填 Jenkinsfile，Credentials 填能拉取该仓库的 GitHub 凭据。
//   - Jenkins 默认端口 8080 与本项目 app 端口冲突，请在 ECS 上把 Jenkins 改为 9090。
//   - jenkins 用户需免密 sudo（部署脚本要用 systemctl / ufw / rsync）。
// =============================================================================

pipeline {
    agent any

    environment {
        DEPLOY_DIR = '/opt/recist'     // 持久化部署目录（数据库/venv 都在这里，不会被 workspace 清掉）
        APP_PORT   = '8080'            // 应用端口（与 deploy_linux.md 一致）
    }

    options {
        timestamps()
        disableConcurrentBuilds()
        // 注意：不要勾选 “Delete workspace before build starts”，否则清掉构建缓存
    }

    stages {

        stage('检出代码') {
            steps {
                // “Pipeline from SCM” 模式下 Jenkins 自动注入 scm；此处直接 checkout scm 即可
                checkout scm
            }
        }

        stage('部署到阿里云本机') {
            steps {
                sh """
                    set -e
                    SUDO=sudo
                    # 1) 确保部署目录存在
                    \$SUDO mkdir -p ${DEPLOY_DIR}

                    # 2) 同步源码到部署目录。
                    #    --exclude 关键：保留目标机已有的数据库(*.db)与虚拟环境(venv)，并排除 .git / node_modules / .workbuddy / 日志
                    \$SUDO rsync -a --delete \
                        --exclude='.git' \
                        --exclude='node_modules' \
                        --exclude='backend/venv' \
                        --exclude='backend/*.db' \
                        --exclude='backend/*.db.bak*' \
                        --exclude='.workbuddy' \
                        --exclude='vite_*.log' \
                        --exclude='*.log' \
                        --exclude='nul' \
                        "\$WORKSPACE/" "${DEPLOY_DIR}/"

                    # 3) 复用现有 deploy.sh 完成：Node/前端构建/venv/.env/systemd/防火墙
                    #    deploy.sh 幂等：venv 复用、仅首次生成随机 SECRET_KEY、自动放行本地防火墙
                    cd ${DEPLOY_DIR}
                    \$SUDO ./deploy.sh --port ${APP_PORT}
                """
            }
        }

        stage('健康检查') {
            steps {
                sh """
                    sleep 3
                    if curl -fsS "http://127.0.0.1:${APP_PORT}/health"; then
                        echo ""
                        echo "部署成功 ✓  公网访问: http://<ECS公网IP>:${APP_PORT}"
                    else
                        echo "健康检查失败，请查看: journalctl -u recist -n 50 --no-pager"
                        exit 1
                    fi
                """
            }
        }
    }

    post {
        success {
            echo "✅ RECIST 已部署/更新到 ${DEPLOY_DIR}，端口 ${APP_PORT}"
        }
        failure {
            echo "❌ 构建/部署失败，请查看上方控制台日志"
        }
    }
}
