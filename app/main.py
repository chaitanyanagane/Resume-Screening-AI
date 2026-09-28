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
        from app.core.database import db_url
        if db_url.startswith("sqlite"):
            logger.warning("Running SQLite in production. Note that SQLite is ephemeral on serverless platforms; configure DATABASE_URL for PostgreSQL persistence.")
        if settings.JWT_SECRET == "hiresense_jwt_super_secret_key_change_in_production":
            logger.warning("Default JWT_SECRET detected in production. Please set a secure secret in environment variables.")
        if not settings.CLOUDINARY_URL:
            logger.warning("CLOUDINARY_URL is not set. Resumes will be processed in-memory.")
            
    # Always ensure tables exist and seed demo/admin accounts if database is fresh
    try:
        from app.core.seed import seed_initial_data
        seed_initial_data()
    except Exception as e:
        logger.error(f"Error initializing or seeding database: {e}")
        
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
        allow_origin_regex=r"^https?://.*\.vercel\.app$",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Rate Limiting configuration
    from slowapi import _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from slowapi.middleware import SlowAPIMiddleware
    from app.core.security import limiter
    
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

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
