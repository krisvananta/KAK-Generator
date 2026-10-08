@echo off
chcp 65001 >nul 2>&1
title KAK Generator - BPKAD Kota Yogyakarta

echo.
echo ============================================================
echo   KAK Generator - Setup ^& Launch
echo ============================================================
echo.

REM --- Cek apakah Python tersedia ---
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python tidak ditemukan!
    echo         Silakan install Python dari https://www.python.org/downloads/
    echo         Pastikan centang "Add Python to PATH" saat instalasi.
    echo.
    pause
    exit /b 1
)

REM --- Install dependencies (skip jika sudah terinstall) ---
echo [1/2] Memeriksa dependensi...
pip install -r "%~dp0requirements.txt" --quiet --disable-pip-version-check
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Gagal menginstall dependensi!
    echo         Pastikan koneksi internet aktif.
    echo.
    pause
    exit /b 1
)
echo       Dependensi siap.
echo.

:menu
echo ============================================================
echo   MENU UTAMA
echo ============================================================
echo [1] Jalankan KAK Generator (Wawancara)
echo [2] Update Data SHBJ (Import dari PDF / Excel)
echo [3] Generate PDF KAK ^& Excel HPS dari File JSON
echo [4] Keluar
echo ============================================================
set /p pilihan="Pilih menu [1/2/3/4]: "

if "%pilihan%"=="1" goto run_bot
if "%pilihan%"=="2" goto import_shbj
if "%pilihan%"=="3" goto render_json
if "%pilihan%"=="4" goto end
echo Pilihan tidak valid!
goto menu

:run_bot
echo.
echo [2/2] Memulai KAK Generator...
echo.
python "%~dp0kak_wizard_cli.py"
echo.
pause
goto menu

:import_shbj
echo.
echo ============================================================
echo   IMPORT DATA SHBJ BARU
echo ============================================================
echo Seret dan lepas (drag-and-drop) file PDF atau Excel ke jendela ini,
echo atau ketikkan path lengkap filenya.
set /p filepath="Path file: "

REM Hapus tanda kutip jika ada
set filepath=%filepath:"=%

echo.
python "%~dp0import_reference.py" "%filepath%"
echo.
pause
goto menu

:render_json
echo.
echo ============================================================
echo   GENERATE PDF ^& EXCEL DARI JSON
echo ============================================================
echo Seret dan lepas file JSON (dari folder output) ke jendela ini,
echo atau ketikkan path lengkap filenya.
set /p filepath="Path file JSON: "

REM Hapus tanda kutip jika ada
set filepath=%filepath:"=%

echo.
python "%~dp0kak_wizard_cli.py" "%filepath%"
echo.
pause
goto menu

:end
exit /b 0
