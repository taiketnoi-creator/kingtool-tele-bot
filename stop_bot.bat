@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo Đang dừng Bot chạy ngầm...
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*bot.py*' -and ($_.Name -eq 'python.exe' -or $_.Name -eq 'pythonw.exe') } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"

echo ✅ Đã dừng Bot thành công!
timeout /t 3
