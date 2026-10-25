# Building the C reference (vvasseur/qcmdpc_decoder) on Windows without cmake/admin

Verified working recipe (2026-09-03), zig cc via pip — no admin, no cmake, no VS:

```powershell
pip install ziglang -i https://pypi.tuna.tsinghua.edu.cn/simple
cd <repo root>   # qcmdpc_decoder-master

# CLASSIC at P1' (4801, 45, 92):
python -m ziglang cc -target x86_64-windows-gnu -O2 -std=gnu11 -include win_compat.h -Iinclude `
  "-DALGO=CLASSIC" "-DINDEX=2" "-DBLOCK_LENGTH=4801" "-DBLOCK_WEIGHT=45" "-DERROR_WEIGHT=92" `
  "-DOUROBOROS=0" "-DWEAK=0" "-DWEAK_P=0" "-DERROR_FLOOR=0" "-DERROR_FLOOR_P=0" `
  src/cli.c src/code.c src/codegen.c src/decoder.c src/decoder_bp.c src/errorgen.c `
  src/qcmdpc_decoder.c src/sparse_cyclic.c src/threshold.c src/xoshiro256plusplus.c `
  -o qcmdpc_classic_p1p.exe -lpthread

# GRAY_BGF at P1 (4801,45,84) / L1 (12323,71,134):
#   same command with "-DALGO=GRAY_BGF" "-DTHRESHOLD_C0=13.53" "-DTHRESHOLD_C1=0.0069722"
#   and the corresponding BLOCK_LENGTH/BLOCK_WEIGHT/ERROR_WEIGHT.
```

Notes:
- ALL -D arguments MUST be quoted in PowerShell (decimal values like 13.53 are
  otherwise tokenized and break the compile).
- Two local shims exist (documented, zero algorithmic change):
  1. src/cli.c: `#ifdef _WIN32` signal() replaces sigaction/SIGHUP;
  2. include/win_compat.h (force-included): aligned_alloc -> malloc
     (AVX disabled in these builds, so 32-byte alignment is a perf hint only;
     malloc keeps free() semantics correct).
- AVX is intentionally NOT defined (zig baseline target; keeps builds portable).
- Weak-key / error-floor studies: add "-DWEAK=1" "-DWEAK_P=<delta>" or
  "-DERROR_FLOOR=1" "-DERROR_FLOOR_P=<kappa>" per README semantics.
- Run: `.\qcmdpc_XXX.exe -T <threads> -N <rounds> -i <max_iter>`;
  final line format: `<total> <iter>:<count> ... >max_iter:<failures>`.
