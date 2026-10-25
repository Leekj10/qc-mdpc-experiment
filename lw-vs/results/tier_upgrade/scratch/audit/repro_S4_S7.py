# -*- coding: utf-8 -*-
"""Auditor C scratch: independent reproduction of phase S4 selection/predictions
and phase S7 selection (5 folds vs the protocol's 'four leave-one-out folds').
Read-only over results; writes nothing."""
import sys
import numpy as np

sys.path.insert(0, r"D:\桌面\TOUGAO - c\实验\qcmdpc-study")
from qcmdpc.stats import cluster_bootstrap_paired

OUT = r"D:\桌面\TOUGAO - c\lw-vs\results\tier_upgrade"
d1 = np.load(OUT + r"\surrogate_S1.npz")
keys = d1["keys"]; deltas = list(d1["deltas"])
FIT_KEYS = list(range(8, 54)); TEST_KEYS = list(range(54, 100))
fit_mask = np.isin(keys, FIT_KEYS); test_mask = ~fit_mask


def fit_eval(X, y, Xte, yte):
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score, brier_score_loss
    mu, sd = X.mean(axis=0), X.std(axis=0); sd[sd == 0] = 1.0
    clf = LogisticRegression(max_iter=2000, C=1e6)
    clf.fit((X - mu) / sd, y)
    p = clf.predict_proba((Xte - mu) / sd)[:, 1]
    ll = -np.mean(yte * np.log(np.clip(p, 1e-12, 1)) + (1 - yte) * np.log(np.clip(1 - p, 1e-12, 1)))
    auc = roc_auc_score(yte, p) if yte.sum() > 0 else float('nan')
    return clf, mu, sd, ll, auc, brier_score_loss(yte, p)


print("=== S4: candidate selection on held-out C0 (reproduce) ===")
j0 = deltas.index(0)
for nm, cols in {"M1": ["n_false"], "M2": ["n_false", "n_true"], "M3": ["n_false", "n_true", "w1"]}.items():
    Xtr = np.stack([d1[c][:, :, j0][fit_mask].ravel() for c in cols], axis=1)
    ytr = d1["fail_0"][fit_mask].ravel().astype(int)
    Xte = np.stack([d1[c][:, :, j0][test_mask].ravel() for c in cols], axis=1)
    yte = d1["fail_0"][test_mask].ravel().astype(int)
    clf, mu, sd, ll, auc, br = fit_eval(Xtr, ytr, Xte, yte)
    print(f"  {nm} {cols}: ll={ll:.6f} auc={auc:.4f} brier={br:.6f}")

# M2 model for predictions (as selected)
cols = ["n_false", "n_true"]
Xtr = np.stack([d1[c][:, :, j0][fit_mask].ravel() for c in cols], axis=1)
ytr = d1["fail_0"][fit_mask].ravel().astype(int)
clf, mu, sd, _, _, _ = fit_eval(Xtr, ytr, Xtr, ytr)

print("=== S4: predicted vs measured RR (M2, fit-keys model) ===")
n_err = d1["nflip"].shape[1]


def pred_arm(j, mask):
    X = np.stack([d1[c][:, :, j][mask].ravel() for c in cols], axis=1)
    return clf.predict_proba((X - mu) / sd)[:, 1].reshape(mask.sum(), n_err)


for j, dl in enumerate(deltas):
    p_test = pred_arm(j, test_mask)
    pred_c0 = pred_arm(j0, test_mask).sum(axis=1)
    rr_pred = float(pred_c0.sum() / max(p_test.sum(axis=1).sum(), 1e-12))
    pera = d1[f"fail_{dl}"][test_mask].sum(axis=1)
    per0 = d1["fail_0"][test_mask].sum(axis=1)
    boot = cluster_bootstrap_paired(per0, pera, n_err, B=10000, seed=20260905)
    print(f"  {cols} delta {dl:+d}: predRR={rr_pred:.6f}  measRR={boot['point']['risk_ratio']:.6f}"
          f"  ci={boot['ci']['risk_ratio']}")

print()
print("=== S7: selection with 5 folds (as coded) vs 4 folds (protocol text) ===")
cands = {"P1": ["n_false", "n_true"], "P2": ["n_false", "n_true", "w1"], "P3": ["n_false", "n_true", "w1", "nflip"]}
for nfold, folds in (("5fold(incl C0)", list(range(5))),
                     ("4fold(excl C0)", [i for i in range(5) if deltas[i] != 0])):
    print(f" -- {nfold} --")
    for cname, cols in cands.items():
        fold_ll = []
        for j in folds:
            tr = [(jj, ddx) for jj, ddx in enumerate(deltas) if jj != j]
            Xtr = np.stack([np.concatenate([d1[c][:, :, jj][fit_mask].ravel() for jj, _ in tr]) for c in cols], axis=1)
            ytr = np.concatenate([d1[f"fail_{ddx}"][fit_mask].ravel().astype(int) for _, ddx in tr])
            Xte = np.stack([d1[c][:, :, j][test_mask].ravel() for c in cols], axis=1)
            yte = d1[f"fail_{deltas[j]}"][test_mask].ravel().astype(int)
            _, _, _, ll, _, _ = fit_eval(Xtr, ytr, Xte, yte)
            fold_ll.append(ll)
        print(f"    {cname} {cols}: mean ll = {np.mean(fold_ll):.6f}  folds={['%.4f' % x for x in fold_ll]}")

print()
print("=== S7: reported folds (P2) ===")
cols = cands["P2"]
for j, dl in enumerate(deltas):
    tr = [(jj, ddx) for jj, ddx in enumerate(deltas) if jj != j]
    Xtr = np.stack([np.concatenate([d1[c][:, :, jj][fit_mask].ravel() for jj, _ in tr]) for c in cols], axis=1)
    ytr = np.concatenate([d1[f"fail_{ddx}"][fit_mask].ravel().astype(int) for _, ddx in tr])
    clf2, mu2, sd2, _, _, _ = fit_eval(Xtr, ytr, Xtr, ytr)
    pred = {}
    for tag, jj in (("C0", deltas.index(0)), (str(dl), j)):
        X = np.stack([d1[c][:, :, jj][test_mask].ravel() for c in cols], axis=1)
        pred[tag] = float(clf2.predict_proba((X - mu2) / sd2)[:, 1].sum())
    rr_pred = pred["C0"] / pred[str(dl)]
    per0 = d1["fail_0"][test_mask].sum(axis=1)
    pera = d1[f"fail_{dl}"][test_mask].sum(axis=1)
    boot = cluster_bootstrap_paired(per0, pera, n_err, B=10000, seed=20260905)
    print(f"  hold out delta {dl:+d}: predRR={rr_pred:.6f}  measRR={boot['point']['risk_ratio']:.6f}"
          f"  ci={boot['ci']['risk_ratio']}")
