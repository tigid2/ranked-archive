@echo off
chcp 65001 >nul
del "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\lol_live_logger.cmd" 2>nul
echo 자동 실행을 해제했어요.
echo 지금 켜져 있는 기록 프로그램은 컴퓨터를 다시 켜면 꺼져요.
echo 바로 끄고 싶으면 작업 관리자에서 pythonw.exe 를 끝내 주세요.
pause
