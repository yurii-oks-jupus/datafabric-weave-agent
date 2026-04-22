# dump_project.ps1

PowerShell utility that concatenates every text file in a repo into a single
Markdown file with unambiguous per-file delimiters. The resulting `.md` is
designed to be copy-pasted from a remote host into a chat client or ticket so
every source file survives the trip.

No Python, no git dependency — just PowerShell 5.1+ / PowerShell 7.

## Quick start

From the repo root on the remote Windows server:

```powershell
powershell -NoProfile -File .\dump_project.ps1
```

Output lands in the current directory with the name
`<repo-folder-name>_dump_<yyyyMMdd-HHmmss>.md`.

## Options

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `-Root`   | `.`     | Directory to dump (relative or absolute). |
| `-Out`    | auto    | Output filename. Default includes repo name + timestamp. |

Examples:

```powershell
# Dump a different repo
powershell -NoProfile -File .\dump_project.ps1 -Root C:\code\datafabric-analytics-agent

# Fixed output name
powershell -NoProfile -File .\dump_project.ps1 -Out analytics_dump.md
```

## What gets included

Every regular text file under `-Root`, recursively.

**Skipped directories** (matched against any path segment):
`.git`, `.adk`, `__pycache__`, `.venv`, `venv`, `node_modules`, `.idea`,
`.vscode`, `.mypy_cache`, `.pytest_cache`, `.ruff_cache`, `dist`, `build`,
`.next`, `.cache`, `.tox`, `.gradle`, `target`.

**Skipped extensions** (binary / artefacts):
`.pyc .pyo .pyd .png .jpg .jpeg .gif .bmp .ico .webp .svg .pdf .zip .tar .gz
.tgz .7z .rar .whl .egg .pem .jks .key .p12 .crt .der .so .dll .exe .o .a
.class .jar .ttf .otf .woff .woff2 .mp3 .mp4 .mov .avi .wav .sqlite .db
.db-shm .db-wal`.

**Also skipped**: the script itself and the output file, plus any file whose
first 8 KB contain a NUL byte (unknown-type binaries).

Edit the `$skipDirs` / `$skipExt` arrays at the top of the script to tweak.

## Output format

```
# Project dump: <repo folder name>
# Generated: <ISO 8601 timestamp>
# Host: <COMPUTERNAME>
# Root: <absolute path>
# Files: <count>

<<<<< BEGIN FILE: relative/path/to/first_file.py >>>>>
...verbatim contents (UTF-8, line endings preserved)...
<<<<< END FILE: relative/path/to/first_file.py >>>>>

<<<<< BEGIN FILE: relative/path/to/second_file.yaml >>>>>
...
<<<<< END FILE: relative/path/to/second_file.yaml >>>>>

```

Paths are forward-slash even on Windows. The delimiter pattern
`<<<<< BEGIN FILE: … >>>>>` was chosen because it does not collide with
Markdown fences (` ``` `) that commonly appear inside source, and is
unlikely to appear in real source code.

## Extracting files back (reference)

Single regex pass works:

```powershell
$raw = Get-Content .\analytics_dump.md -Raw
$pattern = '(?ms)<<<<< BEGIN FILE: (?<p>.+?) >>>>>\r?\n(?<body>.*?)<<<<< END FILE: \k<p> >>>>>'
[regex]::Matches($raw, $pattern) | ForEach-Object {
    $rel = $_.Groups['p'].Value
    $dir = Split-Path $rel -Parent
    if ($dir) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
    Set-Content -LiteralPath $rel -Value $_.Groups['body'].Value -NoNewline -Encoding UTF8
}
```

## Troubleshooting

- **PowerShell 5.1 output looks UTF-16 / "double-sized"**: the script writes
  UTF-8 without BOM via `[System.IO.File]::WriteAllText`, so this should not
  happen. If it does, confirm you ran the script unmodified.
- **Execution policy blocks the script**: run with
  `powershell -NoProfile -ExecutionPolicy Bypass -File .\dump_project.ps1`.
  Bypass applies only to that invocation.
- **Huge dump size**: narrow `-Root` to a subfolder, or add more extensions
  to `$skipExt` at the top of the script.
- **A file you expected is missing**: likely caught by the NUL-byte binary
  sniff, or its extension is in `$skipExt`. Adjust the skip lists.

## Files produced

The dump file (`*_dump_*.md`) is gitignored by default — it should never be
committed.
