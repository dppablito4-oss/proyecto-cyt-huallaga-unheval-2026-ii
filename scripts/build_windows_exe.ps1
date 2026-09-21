param(
    [string]$ReleaseName = "SIVARH-Windows"
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$buildRoot = Join-Path $projectRoot "build"
$distRoot = Join-Path $buildRoot "dist"
$workRoot = Join-Path $buildRoot "pyinstaller"
$releaseRoot = Join-Path $projectRoot "release"
$releaseDir = Join-Path $releaseRoot $ReleaseName
$zipPath = Join-Path $releaseRoot "$ReleaseName.zip"

Set-Location $projectRoot
New-Item -ItemType Directory -Force -Path $buildRoot, $releaseRoot | Out-Null

python -m PyInstaller SIVARH.spec `
    --noconfirm `
    --clean `
    --distpath $distRoot `
    --workpath $workRoot
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller no pudo construir SIVARH."
}

if (Test-Path -LiteralPath $releaseDir) {
    $resolvedRelease = (Resolve-Path -LiteralPath $releaseDir).Path
    if (-not $resolvedRelease.StartsWith($releaseRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Ruta de salida insegura: $resolvedRelease"
    }
    Remove-Item -LiteralPath $resolvedRelease -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $releaseDir | Out-Null
Copy-Item -Path (Join-Path $distRoot "SIVARH\*") -Destination $releaseDir -Recurse -Force

Copy-Item -LiteralPath ".env" -Destination $releaseDir -Force
Copy-Item -LiteralPath "README.md" -Destination $releaseDir -Force
Copy-Item -LiteralPath "documentacion.md" -Destination $releaseDir -Force
Copy-Item -LiteralPath "yoloe-26n-seg.pt" -Destination $releaseDir -Force
Copy-Item -LiteralPath "yolov8n.pt" -Destination $releaseDir -Force
Copy-Item -LiteralPath "frontend" -Destination $releaseDir -Recurse -Force
Copy-Item -LiteralPath "config" -Destination $releaseDir -Recurse -Force
Copy-Item -LiteralPath "prompts" -Destination $releaseDir -Recurse -Force
Copy-Item -LiteralPath "assets" -Destination $releaseDir -Recurse -Force
Copy-Item -LiteralPath "packaging\INICIAR_SIVARH.bat" -Destination $releaseDir -Force
Copy-Item -LiteralPath "packaging\LEEME_PRUEBA.txt" -Destination $releaseDir -Force

$dataDir = Join-Path $releaseDir "data"
New-Item -ItemType Directory -Force -Path `
    (Join-Path $dataDir "frames"), `
    (Join-Path $dataDir "events"), `
    (Join-Path $dataDir "audio\cache"), `
    (Join-Path $releaseDir "output\pdf") | Out-Null
Copy-Item -LiteralPath "data\models" -Destination $dataDir -Recurse -Force
Copy-Item -LiteralPath "data\audio\templates" -Destination (Join-Path $dataDir "audio") -Recurse -Force

if (Test-Path -LiteralPath $zipPath) {
    Remove-Item -LiteralPath $zipPath -Force
}
Compress-Archive -Path (Join-Path $releaseDir "*") -DestinationPath $zipPath -CompressionLevel Optimal

$exePath = Join-Path $releaseDir "SIVARH.exe"
if (-not (Test-Path -LiteralPath $exePath)) {
    throw "No se encontró el ejecutable final: $exePath"
}

$exeSize = (Get-Item -LiteralPath $exePath).Length
$folderSize = (Get-ChildItem -LiteralPath $releaseDir -Recurse -File | Measure-Object Length -Sum).Sum
$zipSize = (Get-Item -LiteralPath $zipPath).Length
[pscustomobject]@{
    Executable = $exePath
    ExecutableMB = [math]::Round($exeSize / 1MB, 2)
    FolderMB = [math]::Round($folderSize / 1MB, 2)
    Zip = $zipPath
    ZipMB = [math]::Round($zipSize / 1MB, 2)
}
