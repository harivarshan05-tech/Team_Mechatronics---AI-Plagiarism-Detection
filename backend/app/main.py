"""
FastAPI Main Application Entry Point.
Sets up CORS, lifespan, routes, and mounts the Frontend Single Page Application.
"""

from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.database import init_db
from app.api.submissions import router as submissions_router
from app.api.analysis import router as analysis_router
from app.api.comparison import router as comparison_router
from app.api.reports import router as reports_router
from app.api.benchmark import router as benchmark_router


# Initialize SQLite database on load
init_db()

app = FastAPI(
    title="AI-Rewritten Code Plagiarism Detector",
    description="Structural and Logical Source Code Plagiarism Detection System",
    version="1.0.0",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(submissions_router)
app.include_router(analysis_router)
app.include_router(comparison_router)
app.include_router(reports_router)
app.include_router(benchmark_router)


@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "service": "AI-Rewritten Code Plagiarism Detector",
        "version": "1.0.0",
    }


# Mount Static Frontend
STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC_DIR.mkdir(exist_ok=True, parents=True)

if (STATIC_DIR / "index.html").exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = STATIC_DIR / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(STATIC_DIR / "index.html")
