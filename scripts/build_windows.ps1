param(
    [string]$Version = "",
    [string]$BuildId = "local"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$Python = if (Test-Path ".venv\Scripts\python.exe") {
    Resolve-Path ".venv\Scripts\python.exe"
} else {
    "python"
}

if (-not $Version) {
    $Version = & $Python -c "from version import VERSION; print(VERSION)"
}

& $Python scripts/set_build_info.py --build-id $BuildId
if ($LASTEXITCODE -ne 0) { throw "Gagal menulis metadata build." }
& $Python scripts/generate_assets.py
if ($LASTEXITCODE -ne 0) { throw "Gagal membuat aset aplikasi." }
& $Python -m PyInstaller --noconfirm --clean DogiPet.spec
if ($LASTEXITCODE -ne 0) { throw "PyInstaller gagal membuat executable." }

$isccCandidates = @(
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
)
$iscc = $isccCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) {
    throw "Inno Setup 6 tidak ditemukan. Instal dari https://jrsoftware.org/isdl.php"
}

$env:DOGIPET_VERSION = $Version
& $iscc installer/DogiPet.iss
if ($LASTEXITCODE -ne 0) { throw "Inno Setup gagal membuat installer." }

$installer = Join-Path $Root "release\DogiPet-Setup.exe"
$hash = (Get-FileHash -Algorithm SHA256 $installer).Hash.ToLowerInvariant()
Set-Content -Encoding ascii -Path "$installer.sha256" -Value "$hash  DogiPet-Setup.exe"
Write-Host "Build selesai: $installer"
