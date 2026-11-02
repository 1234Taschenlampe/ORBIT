# ORBIT APK publisher. Copies APK files only; never publishes ZIP files or QR codes.
# Usage: powershell -ExecutionPolicy Bypass -File .\ORBIT-Publish.ps1
param(
    [string]$Archive = (Join-Path $PSScriptRoot "ORBIT_Alle_25_APKs.zip")
)
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$Repository = "https://github.com/1234Taschenlampe/ORBIT.git"
$ExpectedCount = 25

function Check-Git {
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        throw "Git fuer Windows fehlt. Installation: https://git-scm.com/downloads/win"
    }
}
function Run-Git {
    param([string[]]$Arguments)
    & git @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Git fehlgeschlagen (Exit $LASTEXITCODE): git $($Arguments -join ' ')"
    }
}

Check-Git
if (-not (Test-Path -LiteralPath $Archive -PathType Leaf)) {
    throw "APK-Archiv nicht gefunden: $Archive. Das ZIP muss neben diesem Skript liegen."
}
$TempDir = Join-Path ([System.IO.Path]::GetTempPath()) ("ORBIT-Publish-" + [Guid]::NewGuid().ToString("N"))
$StageDir = Join-Path $TempDir "unpacked"
$RepoDir = Join-Path $TempDir "repo"
New-Item -ItemType Directory -Path $StageDir -Force | Out-Null

try {
    Write-Host "[1/5] APK-Archiv entpacken und Dateien pruefen..."
    Expand-Archive -LiteralPath $Archive -DestinationPath $StageDir
    $Files = @(Get-ChildItem -LiteralPath $StageDir -Recurse -File | Where-Object { $_.Extension -ieq ".apk" })
    if ($Files.Count -ne $ExpectedCount) {
        throw "Abbruch: $ExpectedCount APKs erwartet, $($Files.Count) gefunden."
    }
    $Names = @($Files | ForEach-Object { $_.Name })
    if ((@($Names | Select-Object -Unique)).Count -ne $ExpectedCount) {
        throw "Abbruch: doppelte Dateinamen erkannt."
    }
    foreach ($File in $Files) {
        if ($File.Length -lt 1000) { throw "APK unplausibel klein: $($File.Name)" }
        $Stream = [System.IO.File]::OpenRead($File.FullName)
        try {
            $Head = New-Object byte[] 4
            if ($Stream.Read($Head, 0, 4) -ne 4 -or $Head[0] -ne 80 -or $Head[1] -ne 75 -or $Head[2] -ne 3 -or $Head[3] -ne 4) {
                throw "Keine gueltige ZIP/APK-Kennung: $($File.Name)"
            }
        } finally { $Stream.Dispose() }
    }

    Write-Host "[2/5] GitHub-Repository klonen..."
    Run-Git @("clone", "--depth", "1", $Repository, $RepoDir)
    $ApkDir = Join-Path $RepoDir "apks"
    New-Item -ItemType Directory -Path $ApkDir -Force | Out-Null

    Write-Host "[3/5] Ausschliesslich 25 APK-Dateien nach apks/ kopieren..."
    foreach ($File in $Files) {
        Copy-Item -LiteralPath $File.FullName -Destination (Join-Path $ApkDir $File.Name) -Force
    }

    Push-Location $RepoDir
    try {
        $IdentityName = & git config user.name
        $IdentityEmail = & git config user.email
        if (-not $IdentityName -or -not $IdentityEmail) {
            throw "Git-Autor nicht konfiguriert. Bitte zuerst 'git config --global user.name DEIN_NAME' und 'git config --global user.email DEINE_GITHUB_EMAIL' ausfuehren."
        }

        Write-Host "[4/5] APKs committen..."
        Run-Git @("add", "--", "apks/")
        $Changed = @(& git diff --cached --name-only)
        if ($LASTEXITCODE -ne 0) { throw "git diff fehlgeschlagen." }
        if ($Changed.Count -eq 0) {
            Write-Host "Alle APKs liegen bereits unveraendert auf GitHub. Kein Upload noetig."
            return
        }
        $Invalid = @($Changed | Where-Object { $_ -notmatch '^apks/[^/]+\.apk$' })
        if ($Invalid.Count -gt 0) {
            throw "Sicherheitsabbruch: Dateien ausserhalb von apks/*.apk vorgemerkt: $($Invalid -join ', ')"
        }
        Run-Git @("commit", "-m", "Publish historical ORBIT Android APK builds")

        Write-Host "[5/5] APKs zu GitHub pushen..."
        Run-Git @("push", "origin", "HEAD:main")
        Write-Host ""
        Write-Host "ERFOLG: $ExpectedCount APK-Dateien in ORBIT/apks/ bereitgestellt." -ForegroundColor Green
        Write-Host "Repository: https://github.com/1234Taschenlampe/ORBIT/tree/main/apks"
        Write-Host "Der ORBIT-Katalog erkennt die Downloads automatisch."
    } finally {
        Pop-Location
    }
} finally {
    if (Test-Path -LiteralPath $TempDir) {
        Remove-Item -LiteralPath $TempDir -Recurse -Force -ErrorAction SilentlyContinue
    }
}
