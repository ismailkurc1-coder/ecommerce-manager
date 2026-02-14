@echo off
echo Magaza Dashboard baslatiliyor...
cd /d "%~dp0"
streamlit run dashboard.py
pause
