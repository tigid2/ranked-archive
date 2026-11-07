@echo off
chcp 65001 >nul
echo 기록 프로그램을 창이 보이게 실행할게요. 연습 모드에서 잘 기록되는지 확인할 때 쓰세요.
echo 끄려면 이 창을 닫으면 돼요.
echo.
python "%~dp0logger.py"
if errorlevel 1 py "%~dp0logger.py"
pause
