import argparse
import asyncio
import logging
from fastapi import FastAPI, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import os

# Removed heavy ML imports to allow fast startup of the mock FastAPI server


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("Zarkaan")

app = FastAPI(title="Zarkaan Backend API")

# Allow CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routes
@app.get("/api/status")
async def get_status():
    """Mock API endpoint for system status"""
    return {"status": "operational", "active_cameras": 1, "version": "1.0.0"}

@app.post("/api/upload_video")
async def upload_video(file: UploadFile = File(...)):
    """Mock endpoint to receive video file for analysis"""
    logger.info(f"Received video file for analysis: {file.filename}")
    # Here we would normally save the file and run inference
    # We will simulate a successful upload response
    return JSONResponse(status_code=200, content={"message": "Video received. Processing started.", "filename": file.filename})

# Mount the frontend directory as static files
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_dir):
    logger.info(f"Serving frontend from {frontend_dir}")
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
else:
    logger.warning(f"Frontend directory not found at {frontend_dir}. Please create it to serve the UI.")


if __name__ == "__main__":
    logger.info("Starting Zarkaan Backend Server with FastAPI...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
