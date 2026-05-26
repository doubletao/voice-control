@echo off
setlocal enabledelayedexpansion

echo ============================================
echo   Voice Control - Model Init Script
echo ============================================
echo.

set "PROJECT_DIR=%~dp0"
set "VOSK_DIR=%PROJECT_DIR%models\vosk\vosk-model-small-cn-0.22"
set "VOSK_URL=https://alphacephei.com/vosk/models/vosk-model-small-cn-0.22.zip"
set "VOSK_ZIP=%PROJECT_DIR%models\vosk\vosk-model-small-cn-0.22.zip"

set "GITHUB_MIRROR=https://ghfast.top/"
set "OWW_RELEASE=https://github.com/dscripka/openWakeWord/releases/download/v0.5.1"

for /f "delims=" %%i in ('python -c "import openwakeword,os;print(os.path.join(os.path.dirname(openwakeword.__file__),'resources','models'))" 2^>nul') do set "OWW_DIR=%%i"

if "%OWW_DIR%"=="" (
    echo [ERROR] openwakeword not installed. Run: pip install openwakeword
    pause
    exit /b 1
)

:: ---- Vosk Model ----
echo [1/2] Vosk Chinese Speech Recognition Model
echo --------------------------------------------

if exist "%VOSK_DIR%\am\final.mdl" (
    echo   Already exists, skip.
    goto :oww
)

if not exist "%PROJECT_DIR%models\vosk" mkdir "%PROJECT_DIR%models\vosk"

echo   Downloading vosk-model-small-cn-0.22.zip (~50MB)...
curl -L -o "%VOSK_ZIP%" "%VOSK_URL%"
if errorlevel 1 (
    echo   [ERROR] Download failed. Please download manually:
    echo   %VOSK_URL%
    echo   Extract to: %VOSK_DIR%
    goto :oww
)

echo   Extracting...
powershell -Command "Expand-Archive -Path '%VOSK_ZIP%' -DestinationPath '%PROJECT_DIR%models\vosk' -Force"
if errorlevel 1 (
    echo   [ERROR] Extract failed. Please extract manually.
    goto :oww
)

del "%VOSK_ZIP%" 2>nul
echo   Done!
echo.

:: ---- OpenWakeWord Models ----
:oww
echo [2/2] OpenWakeWord Wake Word Models
echo --------------------------------------------

set "MODELS=embedding_model.tflite embedding_model.onnx melspectrogram.tflite melspectrogram.onnx alexa_v0.1.tflite alexa_v0.1.onnx hey_jarvis_v0.1.onnx hey_mycroft_v0.1.onnx timer_v0.1.onnx hey_rhasspy_v0.1.onnx weather_v0.1.onnx"

set "NEED_DL=0"
for %%m in (%MODELS%) do (
    if not exist "%OWW_DIR%\%%m" set "NEED_DL=1"
)

if "%NEED_DL%"=="0" (
    echo   All models exist, skip.
    goto :done
)

echo   Target: %OWW_DIR%
echo.

for %%m in (%MODELS%) do (
    if exist "%OWW_DIR%\%%m" (
        echo   [skip] %%m
    ) else (
        echo   [download] %%m ...
        curl -L -o "%OWW_DIR%\%%m" "%GITHUB_MIRROR%%OWW_RELEASE%/%%m" 2>nul
        if errorlevel 1 (
            echo   [retry] direct download %%m ...
            curl -L -o "%OWW_DIR%\%%m" "%OWW_RELEASE%/%%m" 2>nul
            if errorlevel 1 (
                echo   [FAIL] %%m
            ) else (
                echo   [ok] %%m
            )
        ) else (
            echo   [ok] %%m
        )
    )
)

echo.

:done
echo ============================================
echo   All done!
echo ============================================
echo.
echo   Run:  python main.py
echo   Or:   python main.py --tray
echo.
echo   Wake words: "Hey Jarvis" "Alexa" "Hey Mycroft"
echo.
pause
