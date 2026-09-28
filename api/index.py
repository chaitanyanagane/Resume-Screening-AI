import sys
from pathlib import Path

# Add project root directory to sys.path so 'app' module imports work on Vercel
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

try:
    from app.main import app
except Exception as e:
    import traceback
    import logging
    err_tb = traceback.format_exc()
    logging.error(f"Error loading FastAPI app in api/index.py: {err_tb}")
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    app = FastAPI()

    @app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"])
    async def fallback_error_handler(full_path: str):
        return JSONResponse(
            status_code=500,
            content={
                "error": "Serverless backend initialization failed",
                "detail": str(e),
                "traceback": err_tb
            }
        )
