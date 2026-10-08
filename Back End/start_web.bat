@echo off
chcp 65001 >nul
title He Thong Tu Van Sach RAG (All-in-One)
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"

echo ============================================================
echo   HE THONG TU VAN SACH RAG (SERVER + CLOUDFLARE TUNNEL)
echo ============================================================
echo.

:: 1. Giai phong cong 8000 neu co process cu dang chiem giu
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do taskkill /f /pid %%a >nul 2>&1

:: 2. Khoi dong Backend Server chay ngam
echo [1/3] Dang khoi dong Backend Server (cong 8000)...
start "Book_RAG_Backend_Server" /min cmd /c "python -m uvicorn main:app --reload --port 8000 --host 0.0.0.0"

:: 3. Mo trinh duyet tren may cua ban
echo [2/3] Dang mo trinh duyet tren may tinh cua ban (localhost:8000)...
start "" powershell -WindowStyle Hidden -NoProfile -Command "Start-Sleep -Seconds 2; Start-Process 'http://localhost:8000'"

:: 4. Khoi tao Cloudflare Tunnel de lay link online
echo [3/3] Dang tao duong link Online qua Cloudflare Tunnel...
echo.
echo ============================================================
echo   [!] HAY TIM VA COPY DUONG LINK CO DUOI: .trycloudflare.com
echo   [!] Gui link do qua Zalo / Messenger de moi nguoi test!
echo.
echo   [!] LUU Y: Giu nguyen cua so nay trong suot luc test!
echo   [!] Khi dong cua so nay, toan bo server se tu dong tat.
echo ============================================================
echo.

"C:\Users\lamq1\cloudflared.exe" tunnel --url http://localhost:8000

:: 5. Tu dong don dep khi tat
taskkill /FI "WINDOWTITLE eq Book_RAG_Backend_Server*" /T /F >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do taskkill /f /pid %%a >nul 2>&1
