
import time, sys
sys.path.insert(0, r"D:/×ÀÃæ/TOUGAO - c/ÊµÑé/qcmdpc-study")
from qcmdpc.decoders import build_decoder
from qcmdpc.generators import KeyPool, make_error_generator
SEED=20260901; P={"id":"P1prime","r":4801,"d":45,"t":90,"n0":2}
pool=KeyPool(SEED,P,"G0",{"type":"random","n_keys":100}); key=pool.keys[8]
gen=make_error_generator(SEED,"G0",key.key_id,P,{"type":"random","n_keys":100},key,None)
dec=build_decoder("C0",{"algo":"bf_parallel","threshold":{"type":"classic"},"max_iter":20},45,90,4801)
t0=time.perf_counter(); n=100
for eid in range(n):
    e=gen(eid); s=key.syndrome_from_global(e); dec(key,s.copy())
print(f"per-proc {n/(time.perf_counter()-t0):.1f} dec/s")
