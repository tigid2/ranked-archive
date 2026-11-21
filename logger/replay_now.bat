@echo off
chcp 65001 >nul
echo 리플레이 프로그램을 지금 한 번 돌려요: 아직 안 올라간 최근 솔로 랭크 판의 리플레이를 받아 디코딩하고 위치 파일을 올려요.
echo 롤 클라이언트를 켠 상태에서 실행해 주세요. 결과는 replay_log.txt에 남아요.
echo.
python "%~dp0replay_worker.py"
if errorlevel 1 py "%~dp0replay_worker.py"
echo.
echo 끝났어요. replay_log.txt 마지막 줄을 확인해 주세요.
pause
