@echo off
chcp 65001 > nul
setlocal

:: Chạy script điều khiển terminal crawl_all.py
python "%~dp0crawl_all.py" %*

endlocal
