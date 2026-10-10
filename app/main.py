"""KPSS Atama Takip - FastAPI Ana Uygulama Fabrikası ve Giriş Noktası."""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import announcements_router, scrapers_router, settings_router
from app.config import settings
from app.core.exceptions.base import KPSSBaseException
from app.core.logging import get_logger, setup_root_logger
from app.infrastructure.database.connection import init_database
from app.services.scheduler import SchedulerService

# Kök loglayıcıyı başlat
setup_root_logger()
logger = get_logger("main")

# Arka plan zamanlayıcı örneği
scheduler_service = SchedulerService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Uygulama yaşam döngüsü yönetimi (Startup & Shutdown)."""
    logger.info("Uygulama başlatılıyor...")
    
    # 1. Veritabanını ve tabloları başlat
    await init_database()

    # 2. Arka plan zamanlayıcısını başlat
    scheduler_service.start()

    yield

    # 3. Kapanırken kaynakları temizle
    logger.info("Uygulama kapatılıyor...")
    scheduler_service.stop()


def create_app() -> FastAPI:
    """FastAPI uygulamasını yapılandırır ve döner."""
    app = FastAPI(
        title=settings.APP_NAME,
        version="1.0.0",
        description="6 Kamu Portalı için KPSS Atama ve Personel Alım Takip API'si",
        lifespan=lifespan,
    )

    # CORS İzinleri (Web UI için)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Global Hata İşleyici (Domain Exceptions)
    @app.exception_handler(KPSSBaseException)
    async def kpss_exception_handler(request: Request, exc: KPSSBaseException):
        logger.error(f"Uygulama Hatası [{exc.error_code}]: {exc.message}")
        return JSONResponse(
            status_code=400,
            content=exc.to_dict(),
        )

    # API Rotalarını Ekle
    app.include_router(announcements_router, prefix="/api")
    app.include_router(scrapers_router, prefix="/api")
    app.include_router(settings_router, prefix="/api")

    @app.get("/health", tags=["Sağlık"])
    async def health_check():
        """Sistem sağlık kontrolü uç noktası."""
        return {
            "status": "healthy",
            "app_name": settings.APP_NAME,
            "env": settings.APP_ENV,
        }

    # Web Dashboard (Statik Dosyalar)
    from pathlib import Path
    from fastapi.staticfiles import StaticFiles

    web_dir = Path(__file__).resolve().parent.parent / "web"
    if web_dir.exists():
        app.mount("/", StaticFiles(directory=str(web_dir), html=True), name="web")

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.APP_DEBUG,
    )
