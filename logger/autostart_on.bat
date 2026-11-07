@echo off
chcp 65001 >nul
set "TARGET=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\lol_live_logger.cmd"
where pythonw >nul 2>nul
if %errorlevel%==0 (set "PY=pythonw") else (set "PY=pyw")
> "%TARGET%" echo @echo off
>> "%TARGET%" echo chcp 65001 ^>nul
>> "%TARGET%" echo start "" %PY% "%~dp0logger.py"
start "" %PY% "%~dp0logger.py"
echo 윈도우를 켤 때마다 기록 프로그램이 조용히 켜지도록 등록했어요. 지금도 실행해 뒀어요.
echo 이 폴더는 옮기지 마세요. 옮겼다면 이 파일을 다시 실행해 주세요.
pause
