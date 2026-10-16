@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo Đang kiểm tra và đóng phiên bot cũ (nếu có)...
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*bot.py*' -and ($_.Name -eq 'python.exe' -or $_.Name -eq 'pythonw.exe') } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
timeout /t 1 /nobreak >nul

echo Đang khởi chạy Bot chạy ngầm (Background)...
start "" "%~dp0.venv\Scripts\pythonw.exe" "%~dp0bot.py"

echo.
echo ========================================================
echo  ✅ BOT ĐÃ CHẠY NGẦM THÀNH CÔNG!
echo  👉 Bạn có thể TẮT cửa sổ này đi, Bot vẫn hoạt động 24/7.
echo  👉 Xem nhật ký hoạt động tại file: bot.log
echo  👉 Muốn dừng Bot, hãy chạy file: stop_bot.bat
echo ========================================================
timeout /t 5
