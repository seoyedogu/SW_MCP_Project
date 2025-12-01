@echo off
REM .env 파일 생성 배치 파일
REM 더블클릭하거나 명령 프롬프트에서 실행: create_env_file.bat

cd /d "%~dp0"

echo OPENAI_API_KEY=your-api-key-here > .env

echo .env 파일이 생성되었습니다.
echo 파일 위치: %CD%\.env
pause


