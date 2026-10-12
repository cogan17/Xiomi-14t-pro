# Requires Windows PowerShell 5+ and Android SDK Platform-Tools.
# Default: read-only verification. -Flash only works on separately approved releases.
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$Image,
    [Parameter(Mandatory=$true)][string]$Manifest,
    [switch]$Flash
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Stop-Unsafe([string]$Message) {
    throw "ROTHKO SAFETY STOP: $Message"
}

$img = (Resolve-Path -LiteralPath $Image -ErrorAction Stop).Path
$json = (Resolve-Path -LiteralPath $Manifest -ErrorAction Stop).Path
$metadata = Get-Content -LiteralPath $json -Raw | ConvertFrom-Json
if ($metadata.device -cne 'rothko') { Stop-Unsafe 'Manifest device must be rothko.' }
if ($metadata.partition -cne 'boot') { Stop-Unsafe 'Only boot is supported (never init_boot, vendor_boot, vbmeta).' }
if ($metadata.firmware -notmatch '^OS3\.[0-9.]+\.WNNIDXM$') { Stop-Unsafe 'Unexpected firmware provenance.' }
if ($metadata.source_commit -cnotmatch '^[a-f0-9]{40}$') { Stop-Unsafe 'Missing exact source commit.' }
if ($metadata.boot_img_sha256 -cnotmatch '^[a-f0-9]{64}$') { Stop-Unsafe 'Invalid boot.img SHA256 metadata.' }
if ($metadata.root -cnotin @('KernelSU','KernelSU-Next','BakaSU')) {
    Stop-Unsafe 'All must be separate files; invalid root flavor.'
}
$file = Get-Item -LiteralPath $img
if ($file.Length -lt 1048576 -or $file.Length -gt 268435456) {
    Stop-Unsafe 'boot.img size is outside expected Android image limits.'
}
$stream = [System.IO.File]::OpenRead($img)
try {
    $header = New-Object byte[] 8
    if ($stream.Read($header, 0, 8) -ne 8 -or
        [Text.Encoding]::ASCII.GetString($header) -cne 'ANDROID!') {
        Stop-Unsafe 'Input is not an Android boot.img. Never fastboot flash an AK3 ZIP or kernel Image.'
    }
} finally {
    $stream.Dispose()
}
$actual = (Get-FileHash -LiteralPath $img -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actual -cne $metadata.boot_img_sha256) {
    Stop-Unsafe 'SHA256 mismatch between boot.img and candidate-manifest.json.'
}
Write-Host 'Image checks: Android boot header PASS; size PASS; SHA256 PASS.'
Write-Host ('Target metadata: rothko / boot / ' + $metadata.firmware)
Write-Host 'WARNING: fastboot cannot independently confirm installed firmware or vendor ABI.'

$localTool = Join-Path $PSScriptRoot 'fastboot.exe'
if (Test-Path -LiteralPath $localTool) {
    $fastboot = $localTool
} else {
    $tool = Get-Command fastboot.exe -ErrorAction SilentlyContinue
    if ($null -eq $tool) {
        Stop-Unsafe 'fastboot.exe missing; install official Android SDK Platform-Tools.'
    }
    $fastboot = $tool.Source
}

# Fastboot often prints getvar values to stderr; capture both output streams.
function Read-Fastboot([string[]]$Arguments) {
    $result = (& $fastboot @Arguments 2>&1 | Out-String)
    $exit = $LASTEXITCODE
    if ($exit -ne 0) { Stop-Unsafe ("fastboot " + ($Arguments -join ' ') + " failed: " + $result) }
    return $result
}
$deviceLines = @((Read-Fastboot @('devices')) -split '\r?\n' |
    Where-Object { $_ -match '^\S+\s+fastboot\s*$' })
if ($deviceLines.Count -ne 1) { Stop-Unsafe 'Exactly one connected fastboot device is required.' }
$product = Read-Fastboot @('getvar','product')
if ($product -notmatch '(?im)^\s*(?:\(bootloader\)\s*)?product:\s*rothko\s*$') {
    Stop-Unsafe ('Bootloader product is not verified rothko: ' + $product)
}
$slot = Read-Fastboot @('getvar','current-slot')
if ($slot -notmatch '(?im)^\s*(?:\(bootloader\)\s*)?current-slot:\s*a\s*$') {
    Stop-Unsafe 'Active slot must be A; historical slot B unbootable. No slot changes allowed.'
}
$unlocked = Read-Fastboot @('getvar','unlocked')
if ($unlocked -notmatch '(?im)^\s*(?:\(bootloader\)\s*)?unlocked:\s*(?:yes|true)\s*$') {
    Stop-Unsafe 'Bootloader unlock status not confirmed.'
}
$userspace = Read-Fastboot @('getvar','is-userspace')
if ($userspace -notmatch '(?im)^\s*(?:\(bootloader\)\s*)?is-userspace:\s*(?:no|false)\s*$') {
    Stop-Unsafe 'Expected bootloader fastboot, not fastbootd.'
}
Write-Host 'Fastboot checks: one device / rothko / active A / unlocked / bootloader mode PASS.'

if ($metadata.approved_for_flash -ne $true) {
    Write-Warning 'CANDIDATE NOT APPROVED: flashing blocked, regardless of -Flash.'
    exit 2
}
if (-not $Flash) {
    Write-Host 'Read-only preflight PASSED. No changes to the phone.'
    Write-Host 'Run again with -Flash only after verifying firmware, vendor ABI and backup off-device.'
    exit 0
}
Write-Warning 'A flash can brick the device or lose root; backup and emergency stock recovery are required.'
$confirmation = Read-Host 'Type exactly FLASH ROTHKO BOOT_A to authorize the single partition write'
if ($confirmation -cne 'FLASH ROTHKO BOOT_A') { Stop-Unsafe 'Flash cancelled.' }
& $fastboot flash boot_a $img
if ($LASTEXITCODE -ne 0) { Stop-Unsafe 'Fastboot flashing failed. Do NOT reboot blindly; inspect logs.' }
Write-Host 'fastboot reported success for boot_a. NO automatic reboot; verify before manually rebooting.'
