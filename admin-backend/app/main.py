"""
类级注释：管理系统后端应用入口
FastAPI 应用主文件
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import get_settings
from app.routers import feishu, sms, system, logs
from app.routers import auth

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    函数级注释：应用生命周期管理
    启动时一次性加载 JSON 配置到内存
    """
    from app.core.storage import get_storage_manager
    storage = get_storage_manager()
    storage.reload()
    yield


app = FastAPI(
    title=settings.app_name,
    description="火灾检测系统 - 管理后台",
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.backend_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(feishu.router, prefix="/api/v1")
app.include_router(sms.router, prefix="/api/v1")
app.include_router(system.router, prefix="/api/v1")
app.include_router(logs.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")


@app.get("/")
def root():
    """
    函数级注释：根路径
    """
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
def health_check():
    """
    函数级注释：健康检查
    """
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8001,
        reload=settings.debug
    )
