@echo off
REM Runs the earthquake pipeline with the project's own Python.
REM Used by Windows Task Scheduler, but you can also double-click it.
cd /d "%~dp0"
".venv\Scripts\python.exe" src\pipeline.py
