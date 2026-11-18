@echo off
chcp 65001 >nul
cd /d "%~dp0"
rem Pedal Point 이용자 앱(디버그 APK) 빌드 → android\PedalPoint.apk
rem 필요: Android SDK, JDK 17 또는 21

rem JDK: JDK17_HOME > Android Studio 내장 JBR > 흔한 설치 경로의 JDK 17·21 > 기존 JAVA_HOME
if defined JDK17_HOME set "JAVA_HOME=%JDK17_HOME%" & goto :jdk_done
if exist "C:\Program Files\Android\Android Studio\jbr\bin\java.exe" set "JAVA_HOME=C:\Program Files\Android\Android Studio\jbr" & goto :jdk_done
for /d %%J in ("C:\DevTools\Java\*jdk17*" "C:\DevTools\Java\*jdk21*" "C:\Program Files\Eclipse Adoptium\jdk-17*" "C:\Program Files\Eclipse Adoptium\jdk-21*" "C:\Program Files\Java\jdk-17*" "C:\Program Files\Java\jdk-21*" "C:\Program Files\Zulu\zulu-17*" "C:\Program Files\Zulu\zulu-21*") do (
    if exist "%%~J\bin\java.exe" set "JAVA_HOME=%%~J" & goto :jdk_done
)
:jdk_done
echo [준비] JAVA_HOME=%JAVA_HOME%

rem Android SDK 위치 (local.properties가 없을 때만 생성)
if not exist local.properties (
    set "SDK=%ANDROID_HOME%"
    if not defined ANDROID_HOME if exist "C:\DevTools\Android\Sdk" set "SDK=C:\DevTools\Android\Sdk"
    if not defined ANDROID_HOME if exist "%LOCALAPPDATA%\Android\Sdk" set "SDK=%LOCALAPPDATA%\Android\Sdk"
)
if not exist local.properties (
    if not defined SDK (
        echo [오류] Android SDK를 찾지 못했습니다. ANDROID_HOME을 설정하세요.
        pause & exit /b 1
    )
    >local.properties echo sdk.dir=%SDK:\=\\%
)

call "%~dp0gradlew.bat" assembleDebug || goto :fail
copy /y app\build\outputs\apk\debug\app-debug.apk PedalPoint.apk >nul
echo.
echo [완료] android\PedalPoint.apk
echo   휴대폰에 옮겨 설치하거나, USB 디버깅 연결 후: adb install -r PedalPoint.apk
goto :eof

:fail
echo.
echo 빌드에 실패했습니다. 위 메시지를 확인하세요.
pause
exit /b 1
