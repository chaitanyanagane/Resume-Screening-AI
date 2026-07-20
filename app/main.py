import logging
import sys
import traceback
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import Base, engine

# Setup structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("hiresense.api")

# Import routers
from app.api import auth, jobs, candidates, applications, interviews, notes, notifications, exports, analytics, admin, health

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup validation
    logger.info(f"Starting HireSense API in {settings.ENVIRONMENT} mode.")
    
    if settings.ENVIRONMENT == "production":
        if settings.DATABASE_URL.startswith("sqlite"):
            logger.error("SQLite is not supported in production! Set a proper DATABASE_URL.")
            sys.exit(1)
        if settings.JWT_SECRET == "hiresense_jwt_super_secret_key_change_in_production":
            logger.error("Default JWT_SECRET detected in production! Please set a secure secret.")
            sys.exit(1)
        if not settings.CLOUDINARY_URL:
            logger.warning("CLOUDINARY_URL is not set. File uploads will fail.")
            
    # For dev, we use create_all, in prod Alembic should have run
    if settings.ENVIRONMENT == "development":
        logger.info("Initializing SQLite database for development.")
        Base.metadata.create_all(bind=engine)
        
    yield
    
    # Graceful shutdown
    logger.info("Shutting down API. Closing database connections.")
    engine.dispose()
    logger.info("Shutdown complete.")

def create_app() -> FastAPI:
    app = FastAPI(
        title="HireSense AI Enterprise ATS",
        description="Production-ready ATS Backend API",
        version="2.0.0",
        lifespan=lifespan
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Global Exception Handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception on {request.url.path}: {exc}\n{traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={"detail": "An internal server error occurred."}
        )

    # Prefix all routes with /api consistently
    app.include_router(auth.router, prefix="/api")
    app.include_router(jobs.router, prefix="/api")
    app.include_router(candidates.router, prefix="/api")
    app.include_router(applications.router, prefix="/api")
    app.include_router(interviews.router, prefix="/api")
    app.include_router(notes.router, prefix="/api")
    app.include_router(notifications.router, prefix="/api")
    app.include_router(exports.router, prefix="/api")
    app.include_router(analytics.router, prefix="/api")
    app.include_router(admin.router, prefix="/api")
    app.include_router(health.router, prefix="/api")

    return app

app = create_app()
