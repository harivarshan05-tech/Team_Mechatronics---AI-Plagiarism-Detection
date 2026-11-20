@echo off
title VeritasCode - AI Plagiarism Engine Server
cd /d "c:\project hackathon"

echo ===================================================
echo   VeritasCode: AI-Rewritten Code Plagiarism Engine
echo ===================================================
echo Starting FastAPI + Uvicorn server on http://localhost:8000...
echo.

"C:\Users\prasa\AppData\Local\Programs\Python\Python313\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --app-dir backend

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Server stopped with error code %ERRORLEVEL%.
    pause
)
