@echo off
chcp 65001 >nul
echo 기록 프로그램에 필요한 것들을 설치할게요. (1~2분 걸려요)
python -m pip install --upgrade mss numpy opencv-python certifi
if errorlevel 1 py -m pip install --upgrade mss numpy opencv-python certifi
echo.
echo 설치가 끝났어요. 이 창은 닫아도 돼요.
pause
