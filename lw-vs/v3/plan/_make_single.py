# -*- coding: utf-8 -*-
"""Create single-column versions of the current EN/ZH manuscripts.

EN: IEEEtran onecolumn (wide single column, figures stay at 7.16 in).
ZH: ctexart onecolumn (A4, same margins as the two-column mirror).
Outputs: lw-vs/v3/single/{en,zh}/main.tex + refs.bib.
"""
import shutil
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / "single"

# English
en = (BASE / "en" / "main.tex").read_text(encoding="utf-8")
en = en.replace(r"\documentclass[lettersize,journal]{IEEEtran}",
                r"\documentclass[lettersize,journal,onecolumn]{IEEEtran}")
en = en.replace(r"\graphicspath{{../figures/}}", r"\graphicspath{{../../figures/}}")
(OUT / "en").mkdir(parents=True, exist_ok=True)
(OUT / "en" / "main.tex").write_text(en, encoding="utf-8")
shutil.copyfile(BASE / "en" / "refs.bib", OUT / "en" / "refs.bib")

# Chinese
zh = (BASE / "zh" / "main.tex").read_text(encoding="utf-8")
zh = zh.replace(r"\documentclass[UTF8,a4paper,10pt,twocolumn]{ctexart}",
                r"\documentclass[UTF8,a4paper,10pt,onecolumn]{ctexart}")
zh = zh.replace(r"\graphicspath{{../figures/}}", r"\graphicspath{{../../figures/}}")
zh = zh.replace(r"\begin{document}", "\\begin{document}\n\\sloppy")
(OUT / "zh").mkdir(parents=True, exist_ok=True)
(OUT / "zh" / "main.tex").write_text(zh, encoding="utf-8")
shutil.copyfile(BASE / "zh" / "refs.bib", OUT / "zh" / "refs.bib")

print("wrote", OUT / "en" / "main.tex")
print("wrote", OUT / "zh" / "main.tex")
