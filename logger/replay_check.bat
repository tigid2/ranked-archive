@echo off
chcp 65001 >nul
echo 리플레이 프로그램 점검: 롤 클라이언트 연결, 리플레이 폴더, 디코더, 최근 솔로 랭크 판의 리플레이 상태를 보여 줘요.
echo 아무것도 받거나 올리지 않아요. 롤 클라이언트를 켠 상태에서 실행해 주세요.
echo.
python "%~dp0replay_worker.py" --check
if errorlevel 1 py "%~dp0replay_worker.py" --check
pause
