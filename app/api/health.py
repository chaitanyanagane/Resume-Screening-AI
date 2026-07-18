from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, timezone

from app.core.database import get_db

router = APIRouter(tags=["health"])

@router.get("/health")
def health_check_endpoint(db: Session = Depends(get_db)):
    health_status = {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat(), "database": "disconnected"}
    try:
        db.execute(text("SELECT 1"))
        health_status["database"] = "connected"
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["error"] = str(e)
        
    return health_status
