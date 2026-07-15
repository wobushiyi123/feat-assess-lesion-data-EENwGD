# RECIST病灶评估系统

基于RECIST 1.1标准的智能肿瘤病灶评估系统，采用 **Vue3 + Python FastAPI** 全栈架构。

## 项目结构

```
.
├── backend/                # Python后端
│   ├── app/
│   │   ├── api/           # API路由
│   │   ├── core/          # 核心配置
│   │   ├── models/        # 数据库模型
│   │   ├── schemas/       # Pydantic模型
│   │   └── services/      # 业务逻辑
│   ├── scripts/           # 工具脚本
│   ├── requirements.txt   # Python依赖
│   └── .env               # 环境配置
├── src/                    # 前端
│   ├── api/               # API调用
│   ├── views/             # 页面
│   ├── utils/             # 工具函数
│   └── ...
├── package.json
└── vite.config.js
```

## 快速开始

### 1. 一键启动

Windows:
```bash
start_all.bat
```

PowerShell:
```powershell
.\start_all.ps1 start   # 启动
.\start_all.ps1 stop    # 停止
.\start_all.ps1 status  # 查看状态
```

### 2. 手动启动后端 (Python)

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
python scripts\init_db.py
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

### 3. 启动前端 (Vue3)

```bash
npm install
npm run dev
```

访问 http://localhost:5173

### 4. 默认账号

| 角色 | 账号 | 密码 |
|-----|------|------|
| 管理员 | admin | admin123 |
| 医生 | doctor | doctor123 |

## 功能特性

### 核心功能
- RECIST 1.1标准评估
- 靶病灶、非靶病灶、新病灶综合判断
- 整体疗效自动评价
- Excel数据导入导出
- 多周期趋势分析

### 智能分析（Python AI驱动）
- 风险评分 (0-100)
- AI趋势预测（线性回归）
- 异常检测 (Z-Score)
- 客观缓解率 (ORR) 计算
- 疾病控制率 (DCR) 计算
- 智能建议生成

### 数据可视化
- 评估结果饼图
- 趋势分析图表
- 实时统计仪表盘

## API文档

启动后端后访问: http://localhost:8080/docs

### 主要API:
- `POST /api/auth/login` - 用户登录
- `GET /api/subjects` - 受试者列表
- `POST /api/assessments/calculate` - 实时计算评估
- `POST /api/assessments` - 创建评估记录
- `GET /api/analysis/trend/{id}` - 受试者趋势分析
- `GET /api/analysis/statistics` - 总体统计
- `POST /api/data/import` - Excel导入
- `GET /api/data/export` - 数据导出

## 技术栈

### 前端
- Vue 3.4
- Element Plus 2.6
- Vue Router 4
- Axios
- ECharts 5
- Vite 5

### 后端
- FastAPI 0.109
- SQLAlchemy 2.0
- Pydantic 2.5
- openpyxl
- JWT (python-jose) + bcrypt

### 数据库
- SQLite（默认，开箱即用）
- 配置文件位于 `backend/app/core/database.py`

## 网络访问

前端 `vite.config.js` 中已配置 `host: '0.0.0.0'`，同网络的人可以通过你的IP访问。

后端启动时已绑定 `0.0.0.0:8080`。

## License

MIT
