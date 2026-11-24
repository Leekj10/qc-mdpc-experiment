# Same-pool independent C replication

This folder reproduces the primary paired comparison with an **independent C
implementation** on the **exact same (H, e) instances** used by the Python
carrier. It is not a second population estimate: the instance file is exported
from the Python formal pool and read by the C runner.

## Result

| Group | Keys | C0 failures | FRO-2 failures | Python C0 / FRO-2 | Per-key match |
|---|---:|---:|---:|---|---|
| G0 (RAND) | 92 | 282 | 68 | 282 / 68 | exact |
| G2_d12 (TYPE-I) | 94 | 372 | 68 | 372 / 68 | exact |
| G3 (NCW-shallow) | 92 | 141 | 31 | 141 / 31 | exact |

`results/per_key_replication.csv` lists all 278 keys with the C and Python
per-key counts. Every row matches.

## Why the carrier must continue after a blocked round

The Python carrier (`bf_parallel`) continues to the iteration budget when a
round produces no flips. The reference C `CLASSIC` decoder exits early on such
a round (`&& !dec->blocked`). For C0 the two are outcome-equivalent because the
state no longer changes; for a **one-shot** offset they are not: the offset is
removed in the next round, so the continued run can recover.

`decoder_static_noblock.c` is the static carrier with that one early-exit
condition removed. With it, the C implementation reproduces the Python counts
exactly. With the reference's early exit, G0 gives FRO-2 **145** (C0 stays
282), which is the population-level value; that difference is the blocked-round
semantics, not a key-pool effect. This is why the paper defines the
continuation rule explicitly.

## Files

- `export_instances.py` — exports the Python formal-pool keys/errors to the
  binary format read by `runner.c`.
- `runner.c` — reads the binary, builds H from the exported supports, runs
  `qcmdpc_decode(dec, 20)`, and prints per-key failure counts.
- `decoder_static_noblock.c` — `实验/qcmdpc-study/static_build/decoder_static.c`
  with the CLASSIC blocked early exit removed (one line).
- `results/` — per-key C counts and the combined CSV.

## Build

From `实验/qcmdpc_decoder_ref/qcmdpc_decoder-master`:

```bash
SRCS="src/code.c src/sparse_cyclic.c src/threshold.c \
      ../../../lw-vs/scripts/replication/decoder_static_noblock.c \
      ../../../lw-vs/scripts/replication/runner.c"
BASE='-target x86_64-windows-gnu -O2 -std=gnu11 -include win_compat.h -Iinclude \
 -DALGO=CLASSIC -DINDEX=2 -DBLOCK_LENGTH=4801 -DBLOCK_WEIGHT=45 \
 -DERROR_WEIGHT=92 -DOUROBOROS=0 -DWEAK=0 -DWEAK_P=0 \
 -DERROR_FLOOR=0 -DERROR_FLOOR_P=0 -DSTATIC_SEMANTICS'
python -m ziglang cc $BASE -DFIRST_ROUND_OFFSET=0 $SRCS -o r0.exe -lm
python -m ziglang cc $BASE -DFIRST_ROUND_OFFSET=2 $SRCS -o r2.exe -lm
```

## Export and run

```bash
# from the project root
python lw-vs/scripts/replication/export_instances.py \
  --group G0 --keys 92 --errors 3000 \
  --out lw-vs/scripts/replication/instances/g0.bin

cd 实验/qcmdpc_decoder_ref/qcmdpc_decoder-master
./r0.exe ../../../lw-vs/scripts/replication/instances/g0.bin > ../.../g0_c0.txt
./r2.exe ../../../lw-vs/scripts/replication/instances/g0.bin > ../.../g0_fro2.txt
```

G2_d12 uses `--keys 94`; G3 uses `--keys 92` (the NCW pool build is slower).
Instance files are ~50 MB per group and are regenerated, not committed.

## Note on the earlier population run

A population run with *fresh keys* (one key per instance) gives RR ≈ 1.96 on
1,000,000 instances, consistent with the P2 RAND transfer (1.95) but below the
P1′ paired estimate (4.15). That run uses a different estimand and a different
blocked-round semantics (the reference's early exit); it is not the same-pool
replication above.
