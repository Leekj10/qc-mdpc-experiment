# -*- coding: utf-8 -*-
"""Auditor C scratch: reproduce phase_RHO numbers (no decoding). Read-only."""


def main():
    import sys
    sys.path.insert(0, r"D:\桌面\TOUGAO - c\实验\qcmdpc-study")
    sys.path.insert(0, r"D:\桌面\TOUGAO - c\lw-vs\scripts")
    from concurrent.futures import ProcessPoolExecutor
    import json
    import exp_surrogate_model as S

    for pt in ({"id": "P1prime", "r": 4801, "d": 45, "t": 92},
               {"id": "P2", "r": 3001, "d": 37, "t": 66}):
        with ProcessPoolExecutor(max_workers=4) as ex:
            res = list(ex.map(S._work_rho, [(pt["id"], pt["r"], pt["d"], pt["t"], ki)
                                            for ki in range(6)]))
        cnt = {dl: {"true": sum(x[3][dl]["true"] for x in res),
                    "false": sum(x[3][dl]["false"] for x in res)} for dl in (0, 1, 2, 3)}
        n_inst = 6 * 300
        print(pt["id"], "(first 6 keys only)")
        for dl in (1, 2, 3):
            dt = (cnt[0]["true"] - cnt[dl]["true"]) / n_inst
            df = (cnt[0]["false"] - cnt[dl]["false"]) / n_inst
            print(f"  delta +{dl}: deferred_true={dt:.6f} avoided_false={df:.6f} rho={df/dt:.6f}")

    arch = json.load(open(r"D:\桌面\TOUGAO - c\lw-vs\results\tier_upgrade\rho_workpoints.json",
                          encoding="utf-8"))
    for pid in ("P1prime", "P2"):
        print("archived", pid, {k: round(v["rho"], 6) for k, v in arch["points"][pid]["rho"].items()})


if __name__ == "__main__":
    main()
