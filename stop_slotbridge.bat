@echo off
chcp 65001 >nul
title SlotBridge - остановка
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\stop_slotbridge.ps1"
if errorlevel 1 pause
