@echo off
chcp 65001 >nul
title Khoi dong Game voi MicroEmulator

echo [1] Kiem tra thu muc 'game' va di chuyen file jar...
if not exist "game" mkdir game
if exist "HaiTacTiHon_v129_b365_21_10_2025.jar" (
    move "HaiTacTiHon_v129_b365_21_10_2025.jar" "game\"
    echo - Da di chuyen file jar vao thu muc game\
) else (
    echo - File jar da nam trong thu muc game hoac khong tim thay o thu muc goc.
)

echo.
echo [2] Kiem tra file MicroEmulator (microemulator.jar)...
set MICROEMU_JAR=
for /r "microemu" %%f in (microemulator.jar) do (
    set MICROEMU_JAR=%%f
)

if "%MICROEMU_JAR%"=="" (
    echo - Chua co file microemulator.jar (chua duoc build tu source code).
    echo - Bat dau build MicroEmulator bang Maven...
    cd microemu\microemulator
    call mvn clean package -DskipTests
    if %ERRORLEVEL% NEQ 0 (
        echo [!] Loi: Khong the build MicroEmulator tu source. Ban da cai dat Maven ^(mvn^) chua?
        pause
        exit /b 1
    )
    cd ..\..
    for /r "microemu\microemulator\target" %%f in (microemulator*.jar) do (
        echo %%f | findstr /v "sources javadoc" >nul
        if not errorlevel 1 set MICROEMU_JAR=%%f
    )
)

if "%MICROEMU_JAR%"=="" (
    echo [!] Van khong tim thay microemulator.jar sau khi build.
    pause
    exit /b 1
)

echo.
echo [3] Khoi dong game tren MicroEmulator...
echo - Su dung Java JRE di kem de mo MicroEmulator cung voi file game.
start "" ".\jre\bin\java.exe" -jar "%MICROEMU_JAR%" "game\HaiTacTiHon_v129_b365_21_10_2025.jar"

echo Hoan thanh!
exit
