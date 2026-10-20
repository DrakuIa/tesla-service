# Установка на Windows-ноутбук. Запуск в PowerShell из этой папки:
#   powershell -ExecutionPolicy Bypass -File .\setup_windows.ps1

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Устанавливаю Python 3.12..."
    winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
    Write-Host "Python установлен. Закройте и откройте PowerShell заново, потом запустите этот скрипт ещё раз."
    exit
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "Устанавливаю Git (нужен для Claude Code)..."
    winget install -e --id Git.Git --accept-package-agreements --accept-source-agreements
}

if (-not (Test-Path .venv)) { python -m venv .venv }
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -r requirements.txt

Write-Host "`nПроверка без машины:"
.\.venv\Scripts\python tesla.py simulate
.\.venv\Scripts\python tesla.py report logs\simulated.asc --car "Тест"

if (-not (Get-Command claude -ErrorAction SilentlyContinue)) {
    Write-Host "`nУстанавливаю Claude Code..."
    irm https://claude.ai/install.ps1 | iex
}

Write-Host "`nГотово. Дальше: поставить драйвер адаптера (см. README.md).`nПрограмма: двойной щелчок по start.bat. Помощник: 'claude' в этой папке."
