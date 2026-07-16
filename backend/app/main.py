"""FastAPI主应用"""
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
# Starlette 不同版本类名不一致：<1.0 为 GzipMiddleware，≥1.0 为 GZipMiddleware，做兼容导入并统一别名
try:
    from starlette.middleware.gzip import GZipMiddleware as GzipMiddleware
except ImportError:  # pragma: no cover - 旧版 starlette
    from starlette.middleware.gzip import GzipMiddleware  # type: ignore
import logging
import os
from sqlalchemy import text
from app.core.config import settings
from app.core.database import engine, Base
from app.api import auth, subjects, assessments, analysis, data_io
from app.api.chat import handle_chat, ChatResponse, ChatRequest
from sqlalchemy.orm import Session
from app.models.database import User
from app.core.database import get_db
from app.api.auth import get_current_user

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建数据库表
Base.metadata.create_all(bind=engine)

# 增量迁移：为 assessments 表添加 visit_name 列（EDC 原始访视名称）
with engine.connect() as conn:
    cols = [r[1] for r in conn.execute(text("PRAGMA table_info(assessments)")).fetchall()]
    if 'visit_name' not in cols:
        conn.execute(text("ALTER TABLE assessments ADD COLUMN visit_name VARCHAR(200)"))
        conn.commit()
        logger.info("Migrated: added assessments.visit_name column")
    else:
        logger.info("assessments.visit_name 列已存在，跳过迁移")

app = FastAPI(
    title=settings.APP_NAME,
    description="基于RECIST 1.1标准的智能肿瘤病灶评估系统",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    # 放行局域网内任意设备访问（localhost / 127.0.0.1 / 192.168.x.x / 10.x.x.x / 172.16-31.x.x，端口任意）
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1|192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Gzip 压缩：压缩 HTML/JS/CSS/JSON 响应，显著降低 ECS 部署时的首屏传输体积（最低 500 字节才压缩）
app.add_middleware(GzipMiddleware, minimum_size=500)

# 注册路由
app.include_router(auth.router)
app.include_router(subjects.router)
app.include_router(assessments.router)
app.include_router(analysis.router)
app.include_router(data_io.router)
# AI 助手问答接口：直接以内联路由注册，确保挂到当前 app 实例（不使用 include_router 以规避模块二次导入导致的实例错配）
@app.post("/api/chat/", response_model=ChatResponse)
@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(
    req: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await handle_chat(req, db, current_user)


@app.get("/")
async def root():
    """根路径：生产模式下返回前端页面，开发模式返回 API 信息"""
    if os.getenv("SERVE_FRONTEND"):
        from pathlib import Path
        _idx = Path(__file__).resolve().parent.parent.parent / "dist" / "index.html"
        if _idx.exists():
            # 不缓存 index.html，保证新发布立即可见
            return FileResponse(str(_idx), headers={'Cache-Control': 'no-cache'})
    return {
        "app": settings.APP_NAME,
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}


@app.on_event("startup")
async def startup_event():
    # 防御性 schema 迁移：为病灶表补充新字段（兼容旧库）
    try:
        from app.core.database import engine
        with engine.connect() as conn:
            # === target_lesions 表迁移 ===
            tl_cols = [r[1] for r in conn.execute(text("PRAGMA table_info(target_lesions)"))]
            tl_additions = {
                "description": "TEXT",
                "baseline_status": "TEXT",
                "exam_date": "TEXT",
                "exam_method": "TEXT",
                "lesion_id": "VARCHAR(50)",
                "size_unit": "VARCHAR(20)",
                "sum_diameter": "FLOAT DEFAULT 0.0",
                "is_checked": "BOOLEAN DEFAULT 1",
                "other_exam_method": "VARCHAR(100)",
                "is_split_fused": "VARCHAR(20)",
                "split_fuse_detail": "TEXT",
                "unmeasurable_reason": "TEXT",
                "current_is_checked": "BOOLEAN",
                "current_exam_date": "VARCHAR(30)",
                "current_exam_method": "VARCHAR(100)",
                "current_other_exam_method": "VARCHAR(100)",
                "current_is_split_fused": "VARCHAR(20)",
                "current_split_fuse_detail": "TEXT",
            }
            for col, col_type in tl_additions.items():
                if col not in tl_cols:
                    conn.execute(text(f"ALTER TABLE target_lesions ADD COLUMN {col} {col_type}"))
                    conn.commit()
                    logger.info(f"已为 target_lesions 补充 {col} 列")

            # === non_target_lesions 表迁移 ===
            ntl_cols = [r[1] for r in conn.execute(text("PRAGMA table_info(non_target_lesions)"))]
            ntl_additions = {
                "description": "TEXT",
                "baseline_status": "TEXT",
                "exam_date": "TEXT",
                "exam_method": "TEXT",
                "lesion_id": "VARCHAR(50)",
                "baseline_is_checked": "BOOLEAN DEFAULT 1",
                "current_is_checked": "BOOLEAN",
                "current_exam_date": "VARCHAR(30)",
                "current_exam_method": "VARCHAR(100)",
            }
            for col, col_type in ntl_additions.items():
                if col not in ntl_cols:
                    conn.execute(text(f"ALTER TABLE non_target_lesions ADD COLUMN {col} {col_type}"))
                    conn.commit()
                    logger.info(f"已为 non_target_lesions 补充 {col} 列")

            # === new_lesions 表迁移 ===
            existing_tables = [r[0] for r in conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))]
            if "new_lesions" not in existing_tables:
                conn.execute(text("""
                    CREATE TABLE new_lesions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        assessment_id INTEGER NOT NULL REFERENCES assessments(id),
                        name VARCHAR(100) NOT NULL,
                        location VARCHAR(100),
                        description TEXT,
                        lesion_id VARCHAR(50),
                        exam_date VARCHAR(30),
                        exam_method VARCHAR(100),
                        other_exam_method VARCHAR(100),
                        notes TEXT
                    )
                """))
                conn.commit()
                logger.info("已创建 new_lesions 表")
            else:
                nl_cols = [r[1] for r in conn.execute(text("PRAGMA table_info(new_lesions)"))]
                nl_additions = {
                    "description": "TEXT",
                    "lesion_id": "VARCHAR(50)",
                    "other_exam_method": "VARCHAR(100)",
                }
                for col, col_type in nl_additions.items():
                    if col not in nl_cols:
                        conn.execute(text(f"ALTER TABLE new_lesions ADD COLUMN {col} {col_type}"))
                        conn.commit()
                        logger.info(f"已为 new_lesions 补充 {col} 列")

            logger.info("schema 迁移检查完成")
    except Exception as e:
        logger.warning(f"schema 迁移检查失败(可忽略): {e}")
    logger.info(f"{settings.APP_NAME} 启动成功")
    logger.info(f"API文档: http://{settings.HOST}:{settings.PORT}/docs")


# 生产模式：单进程同时托管前端静态文件（通过环境变量 SERVE_FRONTEND=1 开启）
# 部署时无需额外 nginx 即可前后端同源一个端口，开发环境不挂载。
if os.getenv("SERVE_FRONTEND"):
    try:
        from fastapi.responses import FileResponse, JSONResponse
        from pathlib import Path
        # backend/app/main.py -> backend/app -> backend -> 项目根
        _dist_dir = Path(__file__).resolve().parent.parent.parent / "dist"
        if _dist_dir.exists():
            _index_html = _dist_dir / "index.html"

            # 单一路由托管前端：真实静态文件直接返回；其余 GET 请求（含刷新子路由）
            # 一律回退 index.html，交给 Vue Router(history 模式) 接管。
            # 注意：/api、/docs、/health 等接口路由已在前面注册并优先匹配，不会进入此处。
            # 可长期缓存的静态资源扩展名（多为带 hash 的文件名，内容不变则 URL 也不变）
            _CACHEABLE_EXT = {
                '.js', '.css', '.png', '.jpg', '.jpeg', '.gif', '.svg',
                '.ico', '.woff', '.woff2', '.ttf', '.eot', '.webp',
            }

            @app.get("/{full_path:path}")
            async def serve_frontend(full_path: str):
                _file = _dist_dir / full_path
                if full_path and _file.exists() and _file.is_file():
                    # 带 hash 的静态资源：强缓存一年（immutable），部署后文件名变化自动失效
                    if _file.suffix.lower() in _CACHEABLE_EXT:
                        return FileResponse(
                            str(_file),
                            headers={'Cache-Control': 'public, max-age=31536000, immutable'}
                        )
                    # HTML/JSON 等：不缓存，保证新发布立即可见
                    return FileResponse(str(_file), headers={'Cache-Control': 'no-cache'})
                if _index_html.exists():
                    return FileResponse(str(_index_html), headers={'Cache-Control': 'no-cache'})
                return JSONResponse(
                    {"detail": "frontend not built, please run: npm run build"},
                    status_code=404,
                )

            logger.info(f"生产模式：已启用前端静态托管(SPA回退) {_dist_dir}")
        else:
            logger.warning(f"SERVE_FRONTEND=1 但前端目录不存在: {_dist_dir}（请先 npm run build）")
    except Exception as e:
        logger.warning(f"挂载前端静态目录失败: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )