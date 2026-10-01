$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath '.venv/Scripts/python.exe')) {
    throw 'Crea el entorno con python -m venv .venv e instala requirements-local.txt. Consulta README-LOCAL.md.'
}
if (-not (Test-Path -LiteralPath 'var/db.sqlite3')) {
    New-Item -ItemType Directory -Force -Path 'var' | Out-Null
    Copy-Item -LiteralPath 'ecom/db.sqlite3' -Destination 'var/db.sqlite3'
}
& ./.venv/Scripts/python.exe manage.py runserver 127.0.0.1:8000 --settings=ecom.settings.local --noreload
