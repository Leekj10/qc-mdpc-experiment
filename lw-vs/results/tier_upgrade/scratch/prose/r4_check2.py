import io
B = chr(92)
for f in ["r4_frozen_en.tex", "r4_frozen_zh.tex"]:
    txt = open(f, encoding="utf-8").read()
    labels, refs = set(), set()
    parts = txt.split(B + "label{")
    for p in parts[1:]:
        labels.add(p.split("}")[0])
    parts = txt.split(B + "ref{")
    for p in parts[1:]:
        refs.add(p.split("}")[0])
    print("==", f)
    print("  refs with no matching label:", sorted(r for r in refs - labels if not r.startswith("#")))
    print("  float labels never referenced:", sorted(l for l in labels - refs if l.startswith(("tab:", "fig:", "alg:"))))
    print("  count labels:", len(labels), "refs:", len(refs))
