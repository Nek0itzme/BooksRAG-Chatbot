@echo off
chcp 65001 >nul
title He Thong Tu Van Sach RAG (Local Web Server)
set PYTHONIOENCODING=utf-8

:: Chuyen huong vao thu muc Back End
if exist "%~dp0Back End" (
    cd /d "%~dp0Back End"
) else (
    cd /d "%~dp0"
)

echo ============================================================
echo   HE THONG TU VAN SACH RAG - MAY CHU CUC BO (LOCAL WEB)
echo ============================================================
echo.

:: 1. Giai phong cong 8000 neu co process cu dang chiem giu
echo [1/2] Kiem tra va giai phong cong 8000...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do taskkill /f /pid %%a >nul 2>&1

:: 2. Mo trinh duyet sau 2 giay
echo [2/2] Dang mo trinh duyet (http://localhost:8000)...
start "" powershell -WindowStyle Hidden -NoProfile -Command "Start-Sleep -Seconds 2; Start-Process 'http://localhost:8000'"

echo.
echo ============================================================
echo   [OK] Server dang chay tai: http://localhost:8000
echo   [!] Nhan Ctrl + C hoac dong cua so nay de tat server.
echo ============================================================
echo.

:: 3. Chay truc tiep Uvicorn FastAPI
python -m uvicorn main:app --reload --port 8000 --host 0.0.0.0

:: 4. Don dep khi tat
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do taskkill /f /pid %%a >nul 2>&1
echo.
echo [!] May chu da dung lai.
pause
