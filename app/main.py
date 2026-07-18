from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import Base, engine

# Import routers
from app.api import auth, jobs, candidates, applications, interviews, notes, notifications, exports, analytics, admin, health

# Create tables for SQLite dev environment. 
# In production with Postgres, Alembic migrations should be used instead.
Base.metadata.create_all(bind=engine)

def create_app() -> FastAPI:
    app = FastAPI(
        title="HireSense AI Enterprise ATS",
        description="Production-ready ATS Backend API",
        version="2.0.0"
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
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
