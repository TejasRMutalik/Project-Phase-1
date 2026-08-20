import os
import sys
import asyncio
import logging

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Ensure backend directory in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db.session import init_db
from src.pipeline.pipeline import SurveillancePipeline
from src.api import shared
from src.api.routes_live import router as live_router
from src.api.routes_upload import router as upload_router
from src.api.routes_config import router as config_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ProjectPhase1")

app = FastAPI(title="Project Phase 1 Backend API", version="1.0.0")


@app.on_event("startup")
def on_startup():
    logger.info("Initializing database...")
    init_db()
    logger.info("Initializing Surveillance Pipeline...")
    shared.pipeline = SurveillancePipeline(shared.CONFIG_PATH)
    shared.MAIN_LOOP = asyncio.get_event_loop()


# Allow CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(live_router)
app.include_router(upload_router)
app.include_router(config_router)

# Mount frontend static directory
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_dir):
    logger.info(f"Serving frontend from {frontend_dir}")
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
else:
    logger.warning(f"Frontend directory not found at {frontend_dir}.")

if __name__ == "__main__":
    logger.info("Starting Project Phase 1 Backend Server on http://0.0.0.0:8000...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
