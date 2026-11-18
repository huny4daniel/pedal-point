@echo off
chcp 65001 >nul
cd /d "%~dp0"

rem 1) 가상환경 + 패키지 (처음 한 번, requirements.txt가 바뀌면 다시 설치)
if not exist ".venv\Scripts\python.exe" (
    echo [준비] 가상환경 생성
    python -m venv .venv || goto :fail
)
fc /b requirements.txt .venv\requirements.installed >nul 2>&1
if errorlevel 1 (
    echo [준비] 패키지 설치
    .venv\Scripts\python.exe -m pip install -q -r requirements.txt || goto :fail
    copy /y requirements.txt .venv\requirements.installed >nul
)

rem 2) 접속 설정 파일이 없으면 예시를 복사하고 비밀번호 입력을 안내
if not exist ".streamlit\secrets.toml" (
    copy ".streamlit\secrets.toml.example" ".streamlit\secrets.toml" >nul
    echo [안내] .streamlit\secrets.toml 을 만들었습니다. MySQL 비밀번호를 입력하고 저장한 뒤 창을 닫으세요.
    notepad ".streamlit\secrets.toml"
)

rem 3) padal DB가 없으면 생성 (run.bat --reset 이면 지우고 새로 생성)
.venv\Scripts\python.exe init_db.py %1 || goto :fail

rem 4) 실행
.venv\Scripts\python.exe -m streamlit run app\main.py
goto :eof

:fail
echo.
echo 실행에 실패했습니다. 위 메시지를 확인하세요.
pause
exit /b 1
