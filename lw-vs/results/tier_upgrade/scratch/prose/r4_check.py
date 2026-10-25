import re
for f in ["r4_frozen_en.tex","r4_frozen_zh.tex"]:
    txt = open(f, encoding="utf-8").read()
    labels = set(l for l in re.findall(r"\label\{([^}]+)\}", txt) if not l.startswith("#"))
    refs = set(re.findall(r"\ref\{([^}]+)\}", txt))
    print("==", f)
    print("  refs with no matching label:", sorted(refs - labels))
    print("  float labels never referenced:", sorted(l for l in labels - refs if l.startswith(("tab:","fig:","alg:"))))
    print("  section labels never referenced:", sorted(l for l in labels - refs if l.startswith("sec:")))
