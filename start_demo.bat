@echo off
echo ===================================================
echo      Project Phase 1 Demo - Startup Script
echo ===================================================
echo.
echo Installing requirements (fastapi, uvicorn)...
pip install fastapi uvicorn

echo.
echo Starting FastAPI Backend Server...
cd backend
python -m uvicorn main:app --reload

pause
