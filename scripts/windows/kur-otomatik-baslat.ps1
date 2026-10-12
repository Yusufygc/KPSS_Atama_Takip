# KPSS Atama Takip - Windows oturum acilisinda otomatik baslatma gorevi kurar / kaldirir.
#   Kurulum :  powershell -ExecutionPolicy Bypass -File scripts\windows\kur-otomatik-baslat.ps1
#   Kaldirma:  powershell -ExecutionPolicy Bypass -File scripts\windows\kur-otomatik-baslat.ps1 -Kaldir
# Yonetici hakki gerekmez (gorev yalnizca bu kullanici icin, oturum acikken calisir).
param([switch]$Kaldir)

$name = "KPSS-Atama-Takip"

if ($Kaldir) {
    Unregister-ScheduledTask -TaskName $name -Confirm:$false -ErrorAction SilentlyContinue
    Write-Output "Gorev kaldirildi: $name"
    exit 0
}

$script = Resolve-Path (Join-Path $PSScriptRoot "baslat-gizli.ps1")
$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$script`""
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -StartWhenAvailable -MultipleInstances IgnoreNew `
    -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit ([TimeSpan]::Zero)

Register-ScheduledTask -TaskName $name -Action $action -Trigger $trigger -Settings $settings `
    -Description "KPSS Atama Takip: tarayici + Telegram bildirimi (oturum acilisinda baslar)" -Force | Out-Null

Write-Output "Gorev kuruldu: $name  (bir sonraki oturum acilisinda baslar)"
Write-Output "Simdi baslatmak icin:  Start-ScheduledTask -TaskName $name"
Write-Output "Durdurmak icin     :  Stop-ScheduledTask  -TaskName $name"
