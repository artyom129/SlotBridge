@echo off
chcp 65001 >nul
title SlotBridge
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start_slotbridge.ps1"
if errorlevel 1 pause
