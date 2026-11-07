@echo off
chcp 65001 >nul
echo 기록 프로그램을 껐다가 다시 켤게요. 게임 중이 아닐 때 실행해 주세요.
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*lol-live-logger*logger.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
timeout /t 2 /nobreak >nul
where pythonw >nul 2>nul
if %errorlevel%==0 (set "PY=pythonw") else (set "PY=pyw")
start "" %PY% "%~dp0logger.py"
echo 다시 켰어요. logger_log.txt 맨 아래에 "기록 프로그램을 시작했어요"가 새로 찍혔는지 보면 돼요.
pause
