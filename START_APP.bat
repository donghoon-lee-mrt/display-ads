@echo off
setlocal enableextensions enabledelayedexpansion

rem ===== Ensure we run from the script directory =====
cd /d "%~dp0"

rem ===== Config =====
set PORT=%1
if "%PORT%"=="" set PORT=8511
set BIND_HOST=0.0.0.0
set OPEN_HOST=127.0.0.1
set LOG_FILE=.streamlit_server.log

rem ===== Load .env.local if present (simple KEY=VALUE) =====
if exist .env.local (
  echo [INFO] Loading .env.local
  for /f "usebackq eol=# tokens=1,* delims==" %%i in (".env.local") do (
    if not "%%i"=="" (
      set %%i=%%j
    )
  )
)

echo.
echo [INFO] Bind host: %BIND_HOST%  port: %PORT%

rem ===== Detect Python venv =====
if exist .venv\Scripts\python.exe (
  set PY_EXE=.venv\Scripts\python.exe
  set PIP_EXE=.venv\Scripts\pip.exe
  set STREAMLIT_EXE=.venv\Scripts\streamlit.exe
  echo [INFO] Using venv Python: %PY_EXE%
) else (
  set PY_EXE=python
  set PIP_EXE=%PY_EXE% -m pip
  echo [WARN] .venv not found. Using system Python.
  rem Windows py launcher fallback (prefers Python 3 via py -3)
  where py >nul 2>&1 && (
    for /f "delims=" %%P in ('py -3 -c "import sys; print(sys.executable)"') do (
      set PY_EXE=py -3
      set PIP_EXE=%PY_EXE% -m pip
      echo [INFO] Using Windows Python launcher: %%P
    )
  )
)

rem ===== Kill processes using the port =====
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :%PORT% ^| findstr LISTENING') do (
  echo [INFO] Killing PID %%a using port %PORT%
  taskkill /PID %%a /F >nul 2>&1
)

rem ===== Ensure requirements are installed (optional) =====
echo [INFO] Ensuring dependencies with %PIP_EXE% ...
%PIP_EXE% install -r requirements.txt --disable-pip-version-check >nul 2>&1

rem ===== Run Streamlit =====
%PIP_EXE% show streamlit >nul 2>&1 || (
  echo [INFO] Installing streamlit via %PIP_EXE% ...
  %PIP_EXE% install streamlit --disable-pip-version-check >nul 2>&1
)

echo [INFO] Starting Streamlit on %BIND_HOST%:%PORT%
if exist %LOG_FILE% del %LOG_FILE% >nul 2>&1
echo [INFO] Python/Streamlit versions >> %LOG_FILE%
%PY_EXE% --version >> %LOG_FILE% 2>&1
%PY_EXE% -m streamlit --version >> %LOG_FILE% 2>&1
start "marketing_1" cmd /c "%PY_EXE% -m streamlit run app.py --server.address=%BIND_HOST% --server.port=%PORT% 1>%LOG_FILE% 2>&1"

echo [INFO] Waiting for server to listen on port %PORT% ...
set /a _waited=0
:WAIT_FOR_SERVER
set SERVER_PID=
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :%PORT% ^| findstr LISTENING') do (set SERVER_PID=%%a)
if defined SERVER_PID goto SERVER_READY
timeout /t 1 >nul
set /a _waited+=1
if %_waited% GEQ 90 goto SERVER_TIMEOUT
goto WAIT_FOR_SERVER

:SERVER_READY
echo [INFO] Server is ready (PID %SERVER_PID%)
echo [INFO] Opening browser...
start http://%OPEN_HOST%:%PORT%/
goto END_SCRIPT

:SERVER_TIMEOUT
echo [WARN] Server did not start within %_waited%s. Showing logs below:
if exist %LOG_FILE% type %LOG_FILE%
echo [HINT] Fix errors above and re-run START_APP.bat
goto END_SCRIPT

:END_SCRIPT
endlocal
exit /b 0




