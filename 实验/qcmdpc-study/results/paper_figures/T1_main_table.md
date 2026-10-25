# T1 main table (source: results/m5_formal/report.json, E/key=3000)

| Group | Decoder | failures/N | DFR | U95 | ratio vs base |
|---|---|---|---|---|---|
| RAND | base (C0) | 282/276000 | 1.022e-03 | 1.127e-03 | 1.0x |
| RAND | FRO-2 (C4) | 68/276000 | 2.464e-04 | 3.007e-04 | 4.1x |
| WEAK-12 | base (C0) | 372/282000 | 1.319e-03 | 1.436e-03 | 1.0x |
| WEAK-12 | FRO-2 (C4) | 68/282000 | 2.411e-04 | 2.943e-04 | 5.5x |
| NCW-$\cap$ (shallow) | base (C0) | 141/276000 | 5.109e-04 | 5.867e-04 | 1.0x |
| NCW-$\cap$ (shallow) | FRO-2 (C4) | 31/276000 | 1.123e-04 | 1.508e-04 | 4.5x |

worst-group log10 U95: base=-2.843, C4=-3.522, improvement=0.679 log10; gate(>=0.5)=PASS; G0 non-inferior=PASS