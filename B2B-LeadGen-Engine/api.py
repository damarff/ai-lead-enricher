from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import subprocess
import os
import signal
import database

app = FastAPI(title="B2B Lead Gen API")

# Allow CORS for local React dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state to track engine process
engine_process = None

class EngineStatus(BaseModel):
    status: str
    pid: int | None = None

@app.get("/api/leads")
def get_leads():
    try:
        jobs = database.get_all_jobs()
        return {"leads": jobs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/status", response_model=EngineStatus)
def get_engine_status():
    global engine_process
    if engine_process and engine_process.poll() is None:
        return EngineStatus(status="running", pid=engine_process.pid)
    return EngineStatus(status="stopped", pid=None)

@app.post("/api/engine/start")
def start_engine():
    global engine_process
    if engine_process and engine_process.poll() is None:
        return {"message": "Engine is already running"}
    
    # Start engine.py in background
    venv_python = os.path.join("venv", "bin", "python")
    engine_process = subprocess.Popen([venv_python, "engine.py"])
    return {"message": "Engine started successfully", "pid": engine_process.pid}

@app.post("/api/engine/stop")
def stop_engine():
    global engine_process
    if not engine_process or engine_process.poll() is not None:
        return {"message": "Engine is not running"}
    
    try:
        os.kill(engine_process.pid, signal.SIGTERM)
        engine_process.wait(timeout=5)
    except Exception as e:
        pass
    
    engine_process = None
    return {"message": "Engine stopped successfully"}
