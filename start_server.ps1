# VeritasCode Detached Server Launcher
param(
    [switch]$Restart
)

$ErrorActionPreference = "SilentlyContinue"

# Check if port 8000 is already in use
$existing = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($existing) {
    if ($Restart) {
        Write-Host "Stopping existing process on port 8000 (PID: $($existing.OwningProcess[0]))..."
        Stop-Process -Id $existing.OwningProcess[0] -Force
        Start-Sleep -Seconds 2
    } else {
        Write-Host "Port 8000 is already running (PID: $($existing.OwningProcess[0]))"
        exit 0
    }
}

$pythonPath = "C:\Users\prasa\AppData\Local\Programs\Python\Python313\python.exe"
$workingDir = "c:\project hackathon"
$cmdLine = "`"$pythonPath`" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --app-dir backend"

# Launch detached via WMI so it stays alive across agent sessions and turns
$res = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{
    CommandLine = $cmdLine
    CurrentDirectory = $workingDir
}

Start-Sleep -Seconds 3

$conn = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($conn) {
    Write-Host "VeritasCode server running on http://127.0.0.1:8000 (PID: $($res.ProcessId))"
} else {
    Write-Host "Warning: Port 8000 not detected yet. ReturnValue: $($res.ReturnValue)"
}
