import sys
B = chr(92)

def load(f):
    return open(f, encoding="utf-8").read()

checks_en = [
    ("F1a tab:added cited", "Tab" + "le~" + B + "ref{tab:added}"),
    ("F1b stray (d)", "Absolute DFR at"),
    ("F2 fig3 caption 9.5", "reduces incorrect flips about"),
    ("F3 fig7 caption", "and specification-formula BIKE-Flip; FRO-2"),
    ("F4 tab:temporal caption", "the fate of one"),
    ("F5 tab:eng cost clause", "cost values are Python"),
    ("F6 tab:added column", "Baseline DFR"),
    ("F7 Fig.ref", "Fig." + B + "ref{"),
    ("F7b Table space ref", "Table " + B + "ref{"),
    ("F8 r_1", "$r_1$"),
    ("F8b v floor", "v{+}1"),
    ("F9 margin delta", "sustains its margin $" + B + "delta$"),
    ("F9b Delta present", B + "Delta"),
    ("F10 AUC duplicate", "held-out-key AUC 0.995"),
    ("F11 sweep", "13.9" + B + "%"),
]
checks_zh = [
    ("Z1 tab:added", "tab:added"),
    ("Z2 contributions", B + "u672c" if False else "贡献有三"),
    ("Z3 tab:temporal caption", "同一 $+2$ 偏移在不同轮次"),
    ("Z4 tab:eng cost clause", "成本数值"),
    ("Z5 r_1", "r_1"),
]
for name, pat in checks_en:
    t = load("r4_final_en.tex")
    print("EN", name, "->", t.count(pat))
for name, pat in checks_zh:
    t = load("r4_final_zh.tex")
    print("ZH", name, "->", t.count(pat))
