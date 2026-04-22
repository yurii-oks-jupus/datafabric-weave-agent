# Concatenates every text file under -Root into one .md with per-file delimiters
# for lossless copy-paste round-trip. Skips caches, binaries, and the script's
# own output. No Python, no git dependency.
#
# Usage:
#   powershell -NoProfile -File .\dump_project.ps1
#   powershell -NoProfile -File .\dump_project.ps1 -Root C:\path\to\repo
#   powershell -NoProfile -File .\dump_project.ps1 -Root . -Out dump.md

param(
    [string]$Root = ".",
    [string]$Out  = ""
)

$ErrorActionPreference = 'Stop'

# ---- Config: edit these lists to taste ----
$skipDirs = @(
    '.git', '.adk', '__pycache__', '.venv', 'venv', 'node_modules',
    '.idea', '.vscode', '.mypy_cache', '.pytest_cache', '.ruff_cache',
    'dist', 'build', '.next', '.cache', '.tox', '.gradle', 'target'
)
$skipExt = @(
    '.pyc', '.pyo', '.pyd',
    '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.ico', '.webp', '.svg',
    '.pdf', '.zip', '.tar', '.gz', '.tgz', '.7z', '.rar',
    '.whl', '.egg',
    '.pem', '.jks', '.key', '.p12', '.crt', '.der',
    '.so', '.dll', '.exe', '.o', '.a', '.class', '.jar',
    '.ttf', '.otf', '.woff', '.woff2',
    '.mp3', '.mp4', '.mov', '.avi', '.wav',
    '.sqlite', '.db', '.db-shm', '.db-wal'
)
# -------------------------------------------

$rootPath = (Resolve-Path -LiteralPath $Root).Path
$rootName = Split-Path $rootPath -Leaf
if (-not $Out) {
    $Out = "{0}_dump_{1}.md" -f $rootName, (Get-Date -Format 'yyyyMMdd-HHmmss')
}
$outAbs = [System.IO.Path]::GetFullPath($Out)

# Resolve absolute path of this script so we can exclude it too.
$scriptAbs = $null
if ($PSCommandPath) {
    $scriptAbs = [System.IO.Path]::GetFullPath($PSCommandPath)
}

function Test-InSkipDir {
    param([string]$FullPath, [string]$RootFull, [string[]]$Names)
    $rel = $FullPath.Substring($RootFull.Length).TrimStart('\','/')
    foreach ($seg in $rel -split '[\\/]+') {
        if ($Names -contains $seg) { return $true }
    }
    return $false
}

function Test-IsBinary {
    param([string]$Path)
    try {
        $fs = [System.IO.File]::OpenRead($Path)
        try {
            $len = [int][Math]::Min(8192, $fs.Length)
            if ($len -eq 0) { return $false }
            $buf = New-Object byte[] $len
            [void]$fs.Read($buf, 0, $len)
            foreach ($b in $buf) { if ($b -eq 0) { return $true } }
            return $false
        } finally { $fs.Dispose() }
    } catch {
        return $true  # unreadable: treat as binary / skip
    }
}

function ConvertTo-RelSlash {
    param([string]$FullPath, [string]$RootFull)
    ($FullPath.Substring($RootFull.Length).TrimStart('\','/')) -replace '\\', '/'
}

$sb = [System.Text.StringBuilder]::new()
[void]$sb.AppendLine("# Project dump: $rootName")
[void]$sb.AppendLine("# Generated: $(Get-Date -Format 'o')")
[void]$sb.AppendLine("# Host: $env:COMPUTERNAME")
[void]$sb.AppendLine("# Root: $rootPath")
[void]$sb.AppendLine("# Files: __COUNT__")
[void]$sb.AppendLine("")

$count = 0
$skipped = 0

Get-ChildItem -LiteralPath $rootPath -Recurse -File -Force |
    Sort-Object FullName |
    ForEach-Object {
        $full = $_.FullName

        if ($full -ieq $outAbs)    { $skipped++; return }
        if ($scriptAbs -and $full -ieq $scriptAbs) { $skipped++; return }
        if (Test-InSkipDir -FullPath $full -RootFull $rootPath -Names $skipDirs) { $skipped++; return }
        if ($skipExt -contains $_.Extension.ToLower()) { $skipped++; return }
        if (Test-IsBinary -Path $full) { $skipped++; return }

        try {
            $content = [System.IO.File]::ReadAllText($full, [System.Text.UTF8Encoding]::new($false))
        } catch {
            Write-Warning "Skipping (read failed): $full"
            $skipped++
            return
        }

        $rel = ConvertTo-RelSlash -FullPath $full -RootFull $rootPath
        [void]$sb.AppendLine("<<<<< BEGIN FILE: $rel >>>>>")
        [void]$sb.Append($content)
        if (-not $content.EndsWith("`n")) { [void]$sb.AppendLine() }
        [void]$sb.AppendLine("<<<<< END FILE: $rel >>>>>")
        [void]$sb.AppendLine("")
        $count++

        if (($count % 50) -eq 0) { Write-Host "  ... $count files" }
    }

$text = $sb.ToString().Replace('__COUNT__', $count.ToString())
[System.IO.File]::WriteAllText($outAbs, $text, [System.Text.UTF8Encoding]::new($false))

$size = (Get-Item -LiteralPath $outAbs).Length
Write-Host ""
Write-Host "Done."
Write-Host "  Included : $count files"
Write-Host "  Skipped  : $skipped files"
Write-Host "  Output   : $outAbs"
Write-Host "  Size     : $([Math]::Round($size/1KB,1)) KB"
