@echo off
rem ==== netsync: DELTA pack ====
rem Requirements before running:
rem   1. A previous FULL pack was confirmed with sync_ok.bat
rem   2. Your git tree is committed clean:  git add -A  +  git commit
setlocal
cd /d "%~dp0.."
:findroot
if exist ".git" goto :rootfound
if "%CD%"=="%~d0\" goto :nogit
cd ..
goto :findroot
:rootfound
rem repo root located: %CD%
if not exist "%~dp0netsync.py" goto :nokit
echo Working directory: %CD%
where python >nul 2>nul
if errorlevel 1 goto :try_py
set "PY=python"
goto :run
:try_py
where py >nul 2>nul
if errorlevel 1 goto :nopy
set "PY=py -3"
goto :run
:run
echo Launching: %PY% netsync\netsync.py pack --out out_sync
%PY% "%~dp0netsync.py" pack --out out_sync
echo.
echo Done. Copy EVERY txt in out_sync out. AFTER the outside side unpacks OK, run sync_ok.bat here.
pause
exit /b 0
:nogit
echo [ERROR] No .git found in parent folders.
echo Put the whole "netsync" folder INSIDE your code repository, then run again.
pause
exit /b 1
:nokit
echo [ERROR] netsync.py not found.
echo Put the whole "netsync" folder INSIDE your repo root folder, then run this bat again.
pause
exit /b 1
:nopy
echo [ERROR] Neither "python" nor "py" was found in PATH.
echo Install Python 3 or add it to PATH, then run again.
pause
exit /b 1
