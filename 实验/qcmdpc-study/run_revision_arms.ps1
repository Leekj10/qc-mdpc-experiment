# Revision experiments (mock-review P0-1 / P0-2), pre-registered in review_round1.md roadmap.
# P0-1: dynamic-semantics CLASSIC (C reference) with FIRST_ROUND_OFFSET {0,2} x {RAND,WEAK12,NCW12}
# P0-2: BACKFLIP comparator x {RAND,WEAK12,NCW12}
# All at P1' (4801,45,92), N=1e6 per cell. ASCII-only literals (PS 5.1 ANSI issue).
$ErrorActionPreference = "Stop"
$study = $PSScriptRoot
$repo = Join-Path (Split-Path $study -Parent) "qcmdpc_decoder_ref\qcmdpc_decoder-master"
$out  = Join-Path $study "results\revision_arms"
New-Item -ItemType Directory -Force -Path $out | Out-Null
Set-Location $repo
$log = Join-Path $out "run_log.txt"
"=== revision arms started $(Get-Date -Format s) ===" | Out-File $log -Encoding utf8

$srcs = "src/cli.c src/code.c src/codegen.c src/decoder.c src/decoder_bp.c src/errorgen.c src/qcmdpc_decoder.c src/sparse_cyclic.c src/threshold.c src/xoshiro256plusplus.c".Split(" ")
$common = @("-target","x86_64-windows-gnu","-O2","-std=gnu11","-include","win_compat.h","-Iinclude",
  "-DINDEX=2","-DBLOCK_LENGTH=4801","-DBLOCK_WEIGHT=45","-DERROR_WEIGHT=92","-DOUROBOROS=0")

$conds = @(
  @{ name = "RAND";   defs = @("-DWEAK=0","-DWEAK_P=0","-DERROR_FLOOR=0","-DERROR_FLOOR_P=0") },
  @{ name = "WEAK12"; defs = @("-DWEAK=1","-DWEAK_P=12","-DERROR_FLOOR=0","-DERROR_FLOOR_P=0") },
  @{ name = "NCW12";  defs = @("-DWEAK=0","-DWEAK_P=0","-DERROR_FLOOR=1","-DERROR_FLOOR_P=12") }
)

function Build-Run($name, $defs, $maxiter) {
  $exe = "rev_$name"
  $ccArgs = $common + $defs + $srcs + @("-o", "$exe.exe", "-lpthread")
  & python -m ziglang cc @ccArgs 2>&1 | Out-Null
  if (-not (Test-Path ".\$exe.exe")) { "COMPILE FAILED: $name" | Out-File $log -Append -Encoding utf8; return }
  $t1 = Get-Date
  $res = & ".\$exe.exe" -T 3 -N 1000000 -i $maxiter 2>&1 | Select-Object -Last 1
  $rt = ((Get-Date) - $t1).TotalSeconds
  "RESULT $name | $res | run_seconds=$([math]::Round($rt))" | Out-File $log -Append -Encoding utf8
}

# P0-1: dynamic-semantics CLASSIC, offsets 0 and +2
foreach ($c in $conds) {
  Build-Run "classic_o0_$($c.name)" (@("-DALGO=CLASSIC") + $c.defs) 20
  Build-Run "classic_o2_$($c.name)" (@("-DALGO=CLASSIC","-DFIRST_ROUND_OFFSET=2") + $c.defs) 20
}
# P0-2: BACKFLIP comparator (TTL defaults per param.h), its own iteration budget
foreach ($c in $conds) {
  Build-Run "backflip_$($c.name)" (@("-DALGO=BACKFLIP") + $c.defs) 100
}
"=== finished $(Get-Date -Format s) ===" | Out-File $log -Append -Encoding utf8
