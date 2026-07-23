@echo off
cd /d "%~dp0"
python scanner.py --html --open --universe 120 %*
