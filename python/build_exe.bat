@echo off
setlocal

py -m pip install -r requirements.txt
py -m pip install pyinstaller
py -m PyInstaller --onefile --windowed --name ESP32_S3_DAQ daq_gui.py

echo.
echo Executavel gerado em:
echo %CD%\dist\ESP32_S3_DAQ.exe
pause
