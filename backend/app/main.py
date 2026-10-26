import os
import sys
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from .database.db import init_db
from .api import datasets, experiments, jobs, export, f1_demo
from ml.utils.hardware import get_hardware_info

# Initialize database schema
init_db()

app = FastAPI(
    title="Privacy-Aware AI Model Unlearning Evaluation Demonstrator",
    description="Research-oriented platform for Machine Unlearning, Responsible AI, and Privacy Evaluation",
    version="1.0.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(datasets.router)
app.include_router(experiments.router)
app.include_router(jobs.router)
app.include_router(export.router)
app.include_router(f1_demo.router)


@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "hardware": get_hardware_info(),
        "python_version": sys.version,
    }


# Static frontend hosting for unified single-command execution
DIST_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../frontend/dist"))
if not os.path.exists(DIST_DIR):
    DIST_DIR = os.path.abspath("./frontend/dist")

if os.path.exists(DIST_DIR):
    assets_dir = os.path.join(DIST_DIR, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    def serve_frontend_spa(full_path: str):
        if full_path.startswith("api") or full_path.startswith("docs") or full_path.startswith("openapi.json"):
            raise HTTPException(status_code=404, detail="Not Found")
        target_path = os.path.join(DIST_DIR, full_path)
        if full_path and os.path.exists(target_path) and os.path.isfile(target_path):
            return FileResponse(target_path)
        return FileResponse(os.path.join(DIST_DIR, "index.html"))
else:
    @app.get("/")
    def root():
        return {
            "title": "Privacy-Aware AI Model Unlearning Evaluation Demonstrator",
            "status": "online",
            "version": "1.0.0",
            "docs_url": "/docs",
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8000, reload=True)
