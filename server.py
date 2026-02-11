import os
from dotenv import load_dotenv
import shutil
import asyncio
from pathlib import Path
from typing import List
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from img_service import GeminiImageGenerator
from loguru import logger
import json
from fastapi.security import APIKeyHeader
from fastapi import Security, Depends, status

# Load .env file
load_dotenv()

CONFIG_FILE = Path("config.json")
MASTER_API_KEY = os.getenv("MASTER_API_KEY", "probaho_master_secret")

def load_cookies():
    """Load cookies from config.json or fallback to .env"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading config.json: {e}")
    
    return {
        "GEMINI_1PSID": os.getenv("GEMINI_1PSID"),
        "GEMINI_1PSIDTS": os.getenv("GEMINI_1PSIDTS")
    }

def save_cookies(psid: str, psidts: str):
    """Save updated cookies to config.json"""
    with open(CONFIG_FILE, "w") as f:
        json.dump({"GEMINI_1PSID": psid, "GEMINI_1PSIDTS": psidts}, f)

API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def get_api_key(api_key_header: str = Security(api_key_header)):
    if api_key_header == MASTER_API_KEY:
        return api_key_header
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing API Key",
    )

app = FastAPI()

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("output_product_set")
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# We will create fresh generators per job for better session isolation

# Simple shared state for progress (In a real app, use Redis or similar)
jobs = {}
LAST_SYNC_TIME = "Never"

class JobStatus(BaseModel):
    job_id: str
    status: str
    progress: float
    message: str
    results: List[str] = []

async def run_generation_task(job_id: str, file_paths: List[Path]):
    jobs[job_id]["status"] = "processing"
    all_results = []
    
    try:
        # Load latest cookies (from config or env)
        cookies = load_cookies()
        
        # Create a fresh generator for each job to ensure clean session (matches img.py pattern)
        job_generator = GeminiImageGenerator(
            psid=cookies.get("GEMINI_1PSID"),
            psidts=cookies.get("GEMINI_1PSIDTS"),
            proxy=os.getenv("GEMINI_PROXY")
        )
        await job_generator.init_client()

        total_files = len(file_paths)
        for idx, file_path in enumerate(file_paths):
            jobs[job_id]["message"] = f"Processing image {idx + 1}/{total_files}: {file_path.name}"
            
            async def progress_update(data):
                jobs[job_id]["message"] = f"Image {idx + 1}/{total_files}: {data['message']}"
                # Update progress roughly
                base_progress = (idx / total_files) * 100
                step_progress = 100 / total_files
                # We can't easily track internal progress of SHOT_LIST here without more complex logic
                # So we just keep it at base for now

            results = await job_generator.generate_for_image(file_path, OUTPUT_DIR, progress_callback=progress_update)
            all_results.extend([f"/outputs/{os.path.basename(r)}" for r in results])
            
            jobs[job_id]["progress"] = ((idx + 1) / total_files) * 100
            jobs[job_id]["results"] = all_results

        jobs[job_id]["status"] = "completed"
        jobs[job_id]["message"] = "All images generated successfully!"
        
    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}")
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["message"] = f"Error: {str(e)}"

@app.post("/upload")
async def upload_images(
    background_tasks: BackgroundTasks, 
    files: List[UploadFile] = File(...),
    api_key: str = Depends(get_api_key)
):
    job_id = f"job_{int(asyncio.get_event_loop().time())}"
    file_paths = []
    
    for file in files:
        file_path = UPLOAD_DIR / file.filename
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        file_paths.append(file_path)
    
    jobs[job_id] = {
        "status": "queued",
        "progress": 0,
        "message": "Files uploaded, starting generation...",
        "results": []
    }
    
    background_tasks.add_task(run_generation_task, job_id, file_paths)
    
    return {"job_id": job_id}

@app.get("/status/{job_id}")
async def get_status(job_id: str, api_key: str = Depends(get_api_key)):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs[job_id]

@app.get("/ping")
async def ping():
    return {"status": "alive", "message": "pong"}

class CookieUpdate(BaseModel):
    psid: str
    psidts: str

@app.post("/admin/sync-cookies")
async def sync_cookies(data: CookieUpdate, api_key: str = Depends(get_api_key)):
    """Secure endpoint for browser extension to sync cookies"""
    try:
        from datetime import datetime
        sync_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        save_cookies(data.psid, data.psidts)
        logger.success(f"Cookies updated via sync API at {sync_time}")
        global LAST_SYNC_TIME
        LAST_SYNC_TIME = sync_time
        return {"status": "success", "message": f"Cookies updated and persisted at {sync_time}"}
    except Exception as e:
        logger.error(f"Sync error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Mount static files (MUST BE LAST to avoid shadowing routes)
app.mount("/outputs", StaticFiles(directory=OUTPUT_DIR), name="outputs")
app.mount("/", StaticFiles(directory=".", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
