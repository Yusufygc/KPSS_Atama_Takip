"""KPSS Atama Takip - FastAPI Ana Uygulama Fabrikası ve Giriş Noktası."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.dependencies import get_announcement_service
from app.api.routes import announcements_router, scrapers_router, settings_router
from app.config import settings
from app.core.constants.settings import SecurityConstants
from app.core.exceptions.base import KPSSBaseException
from app.core.logging import get_logger, setup_root_logger
from app.infrastructure.database.connection import init_database
from app.services.scheduler import SchedulerService

# Kök loglayıcıyı başlat
setup_root_logger()
logger = get_logger("main")

# Arka plan zamanlayıcı örneği
# API ile aynı servis örneği paylaşılır: tarama kilidi ve portal durumları tek yerde tutulur
scheduler_service = SchedulerService(get_announcement_service())


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
    # Prodüksiyonda otomatik API dokümantasyonu kapalıdır
    docs_enabled = not settings.is_production
    app = FastAPI(
        title=settings.APP_NAME,
        version="1.0.0",
        description="6 Kamu Portalı için KPSS Atama ve Personel Alım Takip API'si",
        lifespan=lifespan,
        docs_url="/docs" if docs_enabled else None,
        redoc_url="/redoc" if docs_enabled else None,
        openapi_url="/openapi.json" if docs_enabled else None,
    )

    # CORS: Web UI aynı origin'den sunulur; yalnızca açıkça listelenen kaynaklara izin verilir
    cors_origins = settings.cors_origin_list
    if cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=False,
            allow_methods=["GET", "POST"],
            allow_headers=["Content-Type", "X-API-Key"],
        )

    @app.middleware("http")
    async def security_headers_middleware(request: Request, call_next):
        """Tüm yanıtlara güvenlik başlıklarını ekler."""
        response = await call_next(request)
        for header, value in SecurityConstants.RESPONSE_HEADERS.items():
            response.headers.setdefault(header, value)
        # PDF görüntüleyici ve Swagger arayüzü CSP kısıtlarından etkilenmesin
        path = request.url.path
        if not (path.endswith("/document") or path in SecurityConstants.CSP_EXEMPT_PATHS):
            response.headers.setdefault(
                "Content-Security-Policy", SecurityConstants.CONTENT_SECURITY_POLICY
            )
        return response

    # Global Hata İşleyici (Domain Exceptions)
    @app.exception_handler(KPSSBaseException)
    async def kpss_exception_handler(request: Request, exc: KPSSBaseException):
        logger.error(f"Uygulama Hatası [{exc.error_code}]: {exc.message}")
        if exc.http_status >= 500:
            # Sunucu tarafı hata ayrıntıları (yol, SQL vb.) istemciye sızdırılmaz
            content = {"error_code": exc.error_code, "message": "Sunucu hatası oluştu."}
        else:
            content = exc.to_dict()
        return JSONResponse(status_code=exc.http_status, content=content)

    # API Rotalarını Ekle
    app.include_router(announcements_router, prefix="/api")
    app.include_router(scrapers_router, prefix="/api")
    app.include_router(settings_router, prefix="/api")

    @app.get("/health", tags=["Sağlık"])
    async def health_check():
        """Sistem sağlık kontrolü uç noktası."""
        return {"status": "healthy"}

    # Web Dashboard (Statik Dosyalar)
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
