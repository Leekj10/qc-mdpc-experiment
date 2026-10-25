# L1 C4 transfer study driver (pre-registration v2)
# Compiles 9 C binaries (3 offsets x 3 conditions) and runs 1e6 instances each.
# NOTE: no non-ASCII literals in this file (PowerShell 5.1 reads BOM-less ps1
# as ANSI); all paths derived from $PSScriptRoot at runtime.
$ErrorActionPreference = "Stop"
$study = $PSScriptRoot
$repo = Join-Path (Split-Path $study -Parent) "qcmdpc_decoder_ref\qcmdpc_decoder-master"
$out  = Join-Path $study "results\l1_c4_transfer"
New-Item -ItemType Directory -Force -Path $out | Out-Null
Set-Location $repo
$log = Join-Path $out "run_log.txt"
"=== L1 C4 transfer study, started $(Get-Date -Format s) ===" | Out-File $log -Encoding utf8

$srcs = "src/cli.c src/code.c src/codegen.c src/decoder.c src/decoder_bp.c src/errorgen.c src/qcmdpc_decoder.c src/sparse_cyclic.c src/threshold.c src/xoshiro256plusplus.c".Split(" ")
$common = @("-target","x86_64-windows-gnu","-O2","-std=gnu11","-include","win_compat.h","-Iinclude",
  "-DALGO=CLASSIC","-DINDEX=2","-DBLOCK_LENGTH=12323","-DBLOCK_WEIGHT=71","-DERROR_WEIGHT=134","-DOUROBOROS=0")

$conds = @(
  @{ name = "RAND";   defs = @("-DWEAK=0","-DWEAK_P=0","-DERROR_FLOOR=0","-DERROR_FLOOR_P=0") },
  @{ name = "WEAK12"; defs = @("-DWEAK=1","-DWEAK_P=12","-DERROR_FLOOR=0","-DERROR_FLOOR_P=0") },
  @{ name = "NCW16";  defs = @("-DWEAK=0","-DWEAK_P=0","-DERROR_FLOOR=1","-DERROR_FLOOR_P=16") }
)
$offsets = @(0, 2, 4)

foreach ($o in $offsets) {
  foreach ($c in $conds) {
    $name = "qcmdpc_l1_o$($o)_$($c.name)"
    $defs = $c.defs
    if ($o -gt 0) { $defs += "-DFIRST_ROUND_OFFSET=$o" }
    $t0 = Get-Date
    $ccArgs = $common + $defs + $srcs + @("-o", "$name.exe", "-lpthread")
    & python -m ziglang cc @ccArgs 2>&1 | Out-Null
    if (-not (Test-Path ".\$name.exe")) { "COMPILE FAILED: $name" | Out-File $log -Append -Encoding utf8; continue }
    $tc = ((Get-Date) - $t0).TotalSeconds
    "compiled $name ($([math]::Round($tc))s), running 1e6..." | Out-File $log -Append -Encoding utf8
    $t1 = Get-Date
    $res = & ".\$name.exe" -T 2 -N 1000000 -i 25 2>&1 | Select-Object -Last 1
    $rt = ((Get-Date) - $t1).TotalSeconds
    "RESULT $name | $res | run_seconds=$([math]::Round($rt))" | Out-File $log -Append -Encoding utf8
  }
}
"=== finished $(Get-Date -Format s) ===" | Out-File $log -Append -Encoding utf8
