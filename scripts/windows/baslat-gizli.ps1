# KPSS Atama Takip - pencere acmadan (gizli) baslatici. Gorev Zamanlayici bunu oturum acilisinda calistirir.
# Elle de calistirilabilir:  powershell -ExecutionPolicy Bypass -File scripts\windows\baslat-gizli.ps1
$ErrorActionPreference = "Stop"
$root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $root

# Bu makinede zaten calisiyorsa (ornegin baslat.bat ile) ikinci kopya acma
$port = 8000
if (Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue) {
    Write-Output "Port $port zaten dinleniyor; uygulama calisiyor olabilir. Cikiliyor."
    exit 0
}

$py = Join-Path $root "venv\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = "python" }

# .env degerlerini ezer: yalnizca bu bilgisayardan erisim, otomatik yeniden yukleme kapali
$env:APP_HOST = "127.0.0.1"
$env:APP_DEBUG = "false"
$env:PYTHONUTF8 = "1"

New-Item -ItemType Directory -Force -Path (Join-Path $root "logs") | Out-Null
$out = Join-Path $root "logs\service.out.log"
$err = Join-Path $root "logs\service.err.log"
foreach ($f in @($out, $err)) {
    if ((Test-Path $f) -and ((Get-Item $f).Length -gt 5MB)) { Remove-Item $f -Force }
}

$p = Start-Process -FilePath $py -ArgumentList "run.py" -WorkingDirectory $root `
    -WindowStyle Hidden -RedirectStandardOutput $out -RedirectStandardError $err -PassThru -Wait
exit $p.ExitCode
