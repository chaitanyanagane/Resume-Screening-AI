import re

with open('main.py', 'r') as f:
    content = f.read()

# 1. Replace datetime.utcnow()
content = content.replace('datetime.utcnow()', 'datetime.now(timezone.utc)')

# 2. Add timezone import if missing
if 'from datetime import datetime, timezone' not in content:
    content = content.replace('from datetime import datetime', 'from datetime import datetime, timezone')

# 3. Move uuid and FileResponse to top
if 'import uuid' not in content[:500]:
    content = content.replace('import uuid\n', '')
    content = 'import uuid\n' + content
if 'from fastapi.responses import FileResponse' not in content[:500]:
    content = content.replace('from fastapi.responses import FileResponse\n', '')
    content = content.replace('from fastapi.responses import JSONResponse', 'from fastapi.responses import JSONResponse, FileResponse')

# 4. CORS Origins
content = content.replace(
    'allow_origins=["*"]',
    'allow_origins=os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(",")'
)

# 5. Fix os.path.basename to os.path.realpath in download_resume_endpoint
# We need to make sure the file path is within UPLOAD_DIR
download_fix = """    safe_filename = os.path.basename(filename)
    file_path = os.path.realpath(os.path.join(UPLOAD_DIR, safe_filename))
    if not file_path.startswith(os.path.realpath(UPLOAD_DIR)):
        raise HTTPException(status_code=403, detail="Invalid file path.")
    if not os.path.exists(file_path):"""
content = re.sub(
    r'    safe_filename = os\.path\.basename\(filename\)\n    file_path = os\.path\.join\(UPLOAD_DIR, safe_filename\)\n    if not os\.path\.exists\(file_path\):',
    download_fix,
    content
)

# 6. Replace @app.on_event("startup") with lifespan
lifespan_code = """from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title="HireSense AI API", version="1.0.0", lifespan=lifespan)"""

content = re.sub(r'app = FastAPI\(title="HireSense AI API", version="1\.0\.0"\)', lifespan_code, content)
content = re.sub(r'# Startup DB initialization\n@app\.on_event\("startup"\)\ndef startup_event\(\):\n    init_db\(\)', '', content)

# 7. Remove duplicate router include
content = content.replace("app.include_router(api_router, prefix='/api')\n", "")

with open('main.py', 'w') as f:
    f.write(content)

print("Basic refactors applied.")
