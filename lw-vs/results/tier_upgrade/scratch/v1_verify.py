# V1 adversarial recomputation (read-only; no project files modified)
import sys, math, json
sys.path.insert(0, r"d:/桌面/TOUGAO - c/实验/qcmdpc-study")
from qcmdpc.bikeflip import (derive_bikeflip_affine, binomial_Ft, BIKEFLIP_OFFICIAL)

def z2p(k1, n1, k2, n2):
    p1, p2 = k1/n1, k2/n2
    p = (k1+k2)/(n1+n2)
    se = math.sqrt(p*(1-p)*(1/n1+1/n2))
    return (p1-p2)/se

print("="*30, "A. BIKE-Flip affine derivation")
for (r,d,t), off in BIKEFLIP_OFFICIAL.items():
    a,b,Savg = derive_bikeflip_affine(r,d,t)
    da, db = abs(a-off["a"]), abs(b-off["b"])
    print(f"L r={r} d={d} t={t}: Savg={Savg} da={da:.2e} db={db:.2e}")
a,b,Savg = derive_bikeflip_affine(4801,45,92)
print(f"P1' r=4801 d=45 t=92: a={a!r} b={b!r} Savg={Savg}")
print("  claimed: a=0.008254384572857987 b=12.604481862986894 Savg=1986")

print("="*30, "B. affine vs binomial_Ft gap at P1' (d=45,t=92,n=9602)")
for S in (1500, 1986, 2000, 2500, 3000):
    aff_real = 13.53 + 0.0069722*S
    aff_trunc = int(aff_real)  # C truncation
    ft = binomial_Ft(S, 92, 45, 9602)
    print(f"  S={S}: F_t={ft:.4f} aff_real={aff_real:.4f} aff_trunc={aff_trunc} "
          f"gap_vs_trunc={ft-aff_trunc:.3f} gap_vs_real={ft-aff_real:.3f}")

print("="*30, "C. semantics z-tests")
print(f"  z(71/72000 vs 136/200000) = {z2p(71,72000,136,200000):.3f}  (claim 2.55)")
print(f"  z(11/20000 vs 136/200000) = {z2p(11,20000,136,200000):.3f}  (claim -0.68)")
print(f"  z(111/100000 vs 136/200000) = {z2p(111,100000,136,200000):.3f}  (my V1 run vs dynamic)")
print(f"  z(111/100000 vs 104/100000) = {z2p(111,100000,104,100000):.3f}  (my V1 run vs F3 static 1e5)")

print("="*30, "D. RR decompositions")
rows = [("RAND", 4.147058823529411, 282/276000, 68/276000, 738/1e6, 463/1e6),
        ("TYPE-I", 5.470588235294118, 372/282000, 68/282000, 853/1e6, 425/1e6),
        ("NCW", 4.548387096774193, 141/276000, 31/276000, 107/1e6, 88/1e6)]
for name, rr_static, c0s, f2s, c0d, f2d in rows:
    rr_dyn = c0d/f2d
    print(f"  {name}: RR_static={rr_static:.4f} RR_dyn={rr_dyn:.4f} ratio={rr_static/rr_dyn:.3f} "
          f"C0scale={c0d/c0s:.4f} F2scale={f2d/f2s:.4f} decomp={(c0d/c0s)/(f2d/f2s)*rr_static:.4f}")

print("="*30, "E. power table recomputation")
def fmt(h): return f"{h*3600:.3g}s={h:.4g}h={h/24:.3g}d"
def row(t, dfr, rates, rr=4.5, note=""):
    p = dfr
    n_c0 = 100/p               # instances for ~100 C0 failures
    n_two = 100/(p/rr)         # instances so FRO-2 arm gets ~100 failures
    dec_c0, dec_two = 2*n_c0, 2*n_two
    print(f"  t={t}: p={p:g} N_C0={n_c0:.3g} N_two={n_two:.3g}")
    for label, rate in rates.items():
        print(f"     {label} rate={rate}: C0only={dec_c0/rate/3600:.4g}h two-arm={dec_two/rate/3600:.4g}h")
row(134, 2.1e-6, {"py137.4":137.4, "C1_3922":3922, "C10_19231":19231})
row(168, 7.1e-5, {"py97.4":97.4, "C1_2410":2410, "C10_est":2410*4.9})
row(170, 2.5e-4, {"py86.8":86.8, "C1_2299":2299, "C10_est":2299*4.9})
row(172, 1.958e-3, {"py93.5":93.5, "C1_2143":2143, "C10_est":2143*4.9}, rr=4.476)
row(175, 1.51e-2, {"py87.6":87.6, "C1_1923":1923, "C10_est":1923*4.9})

print("  extrapolation base 168, 34 units to 134:")
p168 = 7.1e-5
for f in (1.56, 2.0, 3.6):
    p134 = p168 / f**34
    n_two = 450/p134
    py_yr = 2*n_two/137.4/3600/24/365.25
    c_yr = 2*n_two/19231/3600/24/365.25
    print(f"    f={f}: p134={p134:.3g} N_two={n_two:.3g} py_years={py_yr:.3g} cT10_years={c_yr:.3g}")
for k in (2,5,10,20,34):
    print(f"    k={k}: {1.56**k:.3g} to {3.6**k:.3g}")

print("="*30, "F. bound-budget schedule (T=10, 19231/s)")
rate = 19231
per_day = rate*86400
for label, days in [("day",1), ("month30",30), ("month31",31), ("year",365)]:
    N = per_day*days
    print(f"  {label}: decodes={N:.3g} bound(rule3)={3/N:.3g}")
print(f"  years to bound 1e-15: {3/1e-15/per_day/365.25:.4g}")

print("  push-down budget (two-arm, instances N=decodes/2):")
for label, days in [("week",7), ("month",30), ("year",365)]:
    inst = per_day*days/2
    p_need = 450/inst
    for f in (1.56, 3.6):
        dk = math.log(p168/p_need)/math.log(f)
        print(f"    {label} f={f}: t={168-dk:.1f}")

print("="*30, "G. slope factors")
py = {168:None, 170:1/6000, 172:13/6000, 175:90/6000, 180:835/6000}
cstatic = {168:37/520000, 170:65/260000, 172:610/360000, 175:3168/210000}
print("  Python per-unit:",
      f"170-172 {(py[172]/py[170])**0.5:.3f}",
      f"172-175 {(py[175]/py[172])**(1/3):.3f}",
      f"175-180 {(py[180]/py[175])**0.2:.3f}")
print("  C static per-unit:",
      f"168-170 {(cstatic[170]/cstatic[168])**0.5:.3f}",
      f"170-172 {(cstatic[172]/cstatic[170])**0.5:.3f}",
      f"172-175 {(cstatic[175]/cstatic[172])**(1/3):.3f}",
      f"168-172 {(cstatic[172]/cstatic[168])**0.25:.3f}")
print("  window16pct:", (195-168)/168, " margin27pct:", (170-134)/134, " 28pct:", (172-134)/134)
print("  6x degradation 1/0.1615 =", 1/0.1615)

print("="*30, "H. misc")
print("  two-round rates l1b: C0 2.0540625 / F2 2.44603125 / neg 2.23184375")
print("  137.4 check: 96000/698.6 =", 96000/698.6)
print("  93.5 check: 144000/1539.7 =", 144000/1539.7)
print("  N for 100 fails t134 with rr4.476:", 450/2.1e-6, "->", 2*(450/2.1e-6)/3922/3600, "h C1")
