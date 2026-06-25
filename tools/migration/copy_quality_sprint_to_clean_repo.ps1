param(
    [Parameter(Mandatory = $true)]
    [string]$SourceRoot,

    [Parameter(Mandatory = $true)]
    [string]$DestRoot,

    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

function Resolve-RootPath {
    param([string]$PathValue)
    return (Resolve-Path -LiteralPath $PathValue).Path
}

function Invoke-RobocopyCategory {
    param(
        [string]$Category,
        [string]$RelativePath
    )

    $source = Join-Path $script:SourceRootResolved $RelativePath
    $dest = Join-Path $script:DestRootResolved $RelativePath

    if (-not (Test-Path -LiteralPath $source)) {
        Write-Host "[SKIP] $Category not present: $RelativePath"
        return
    }

    Write-Host "[COPY] ${Category}: $RelativePath"
    $excludeDirs = @(
        ".git", "Lib", "Scripts", "etc", "share", ".venv", "venv", "env",
        "data\cache", "data\raw", ".pytest_cache", "__pycache__",
        ".ipynb_checkpoints", ".ruff_cache", "tmp", "output", "reports"
    )
    $excludeFiles = @("*.pyc", "*.pyo", "*.parquet", "*.pkl", "*.pickle")
    $args = @($source, $dest, "/E", "/R:1", "/W:1", "/XD") +
        $excludeDirs + @("/XF") + $excludeFiles

    if ($DryRun) {
        $args += "/L"
    }

    & robocopy @args | Write-Host
    if ($LASTEXITCODE -gt 7) {
        throw "robocopy failed for $RelativePath with exit code $LASTEXITCODE"
    }
}

function Copy-RootFile {
    param([string]$RelativePath)

    $source = Join-Path $script:SourceRootResolved $RelativePath
    $dest = Join-Path $script:DestRootResolved $RelativePath

    if (-not (Test-Path -LiteralPath $source)) {
        Write-Host "[SKIP] root file not present: $RelativePath"
        return
    }

    Write-Host "[COPY] root file: $RelativePath"
    if ($DryRun) {
        Write-Host "[DRYRUN] Copy-Item $source -> $dest"
        return
    }

    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $dest) | Out-Null
    Copy-Item -LiteralPath $source -Destination $dest -Force
}

function Copy-ProjectScript {
    $source = Join-Path $script:SourceRootResolved "scripts\run_full_pipeline.py"
    $destDir = Join-Path $script:DestRootResolved "scripts"
    $dest = Join-Path $destDir "run_full_pipeline.py"

    if (-not (Test-Path -LiteralPath $source)) {
        Write-Host "[SKIP] project script not present: scripts\run_full_pipeline.py"
        return
    }

    Write-Host "[COPY] project CLI script: scripts\run_full_pipeline.py"
    if ($DryRun) {
        Write-Host "[DRYRUN] Copy-Item $source -> $dest"
        return
    }

    New-Item -ItemType Directory -Force -Path $destDir | Out-Null
    Copy-Item -LiteralPath $source -Destination $dest -Force
}

function Copy-LightweightProcessedData {
    $sourceDir = Join-Path $script:SourceRootResolved "data\processed"
    $destDir = Join-Path $script:DestRootResolved "data\processed"

    if (-not (Test-Path -LiteralPath $sourceDir)) {
        Write-Host "[SKIP] lightweight data not present: data\processed"
        return
    }

    Write-Host "[COPY] lightweight data outputs: data\processed\*.csv, *.json, *.png"
    $files = Get-ChildItem -LiteralPath $sourceDir -File |
        Where-Object { $_.Extension -in @(".csv", ".json", ".png") }

    foreach ($file in $files) {
        $dest = Join-Path $destDir $file.Name
        if ($DryRun) {
            Write-Host "[DRYRUN] Copy-Item $($file.FullName) -> $dest"
            continue
        }

        New-Item -ItemType Directory -Force -Path $destDir | Out-Null
        Copy-Item -LiteralPath $file.FullName -Destination $dest -Force
    }
}

$script:SourceRootResolved = Resolve-RootPath $SourceRoot

if (-not (Test-Path -LiteralPath $DestRoot)) {
    if ($DryRun) {
        $script:DestRootResolved = $DestRoot
    } else {
        New-Item -ItemType Directory -Force -Path $DestRoot | Out-Null
        $script:DestRootResolved = Resolve-RootPath $DestRoot
    }
} else {
    $script:DestRootResolved = Resolve-RootPath $DestRoot
}

Write-Host "SourceRoot: $script:SourceRootResolved"
Write-Host "DestRoot:   $script:DestRootResolved"
Write-Host "DryRun:     $DryRun"
Write-Host "Safe include categories: src/, src/project/research/, tests/, docs/, docs/research/, configs/, scripts/run_full_pipeline.py, root quality files, lightweight data/processed CSV/JSON/PNG"
Write-Host "Explicit exclusions include Git metadata, virtual environments, caches, parquet/pickle outputs, output/, reports/, and PDF handoff files."

Invoke-RobocopyCategory -Category "source package" -RelativePath "src"
Write-Host "[INFO] src/project/research is included through the source package copy."
Invoke-RobocopyCategory -Category "tests" -RelativePath "tests"
Invoke-RobocopyCategory -Category "documentation" -RelativePath "docs"
Write-Host "[INFO] docs/research is included through the documentation copy."
Invoke-RobocopyCategory -Category "configs" -RelativePath "configs"
Invoke-RobocopyCategory -Category "legacy config" -RelativePath "config"

Copy-ProjectScript

foreach ($file in @(
    "README.md",
    "pyproject.toml",
    "Makefile",
    ".pre-commit-config.yaml",
    ".gitignore"
)) {
    Copy-RootFile -RelativePath $file
}

Copy-LightweightProcessedData

Write-Host "Transfer helper completed. No Git commands were run."
