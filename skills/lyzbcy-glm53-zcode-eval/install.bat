@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel% equ 0 (
    py -3 "%~dp0zcode-instruct.py"
    set "EXIT_CODE=!errorlevel!"
    goto :done
)

where python >nul 2>nul
if %errorlevel% equ 0 (
    python "%~dp0zcode-instruct.py"
    set "EXIT_CODE=!errorlevel!"
    goto :done
)

echo [ERROR] Python 3 was not found. Install Python 3.9 or newer.
echo [错误] 未找到 Python 3。请安装 Python 3.9 或更高版本。
set "EXIT_CODE=1"

:done
echo.
pause
exit /b %EXIT_CODE%
