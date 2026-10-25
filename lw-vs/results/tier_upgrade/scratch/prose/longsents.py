#!/usr/bin/env python
"""Scratch analysis 3: longest prose sentences, floats removed. argv[1]=tex path."""
import re
import statistics
import sys

path = sys.argv[1]
raw = open(path, encoding="utf-8").read()
text = re.sub(r"(?<!\\)%.*", " ", raw)
text = text.split("\\begin{document}", 1)[-1]
for env in ["figure*", "figure", "table*", "table", "algorithm", "algorithmic"]:
    text = re.sub(r"\\begin\{%s\}" % re.escape(env), " <<<F>>> ", text)
    text = re.sub(r"\\end\{%s\}" % re.escape(env), " ", text)
out = []
for seg in re.split(r"<<<F>>>", text):
    out.append(seg)
text = " ".join(out)
text = re.sub(r"\\cite\{[^}]*\}", "[CIT]", text)
text = re.sub(r"\\ref\{[^}]*\}", "REF", text)
text = re.sub(r"\\label\{[^}]*\}", " ", text)
text = re.sub(r"\\emph\{([^}]*)\}", r"\1", text)
text = re.sub(r"\\textbf\{([^}]*)\}", r"\1", text)
text = re.sub(r"\\texttt\{([^}]*)\}", r"\1", text)
text = re.sub(r"\\path\{([^}]*)\}", r"\1", text)
text = re.sub(r"\\url\{([^}]*)\}", r"\1", text)
text = re.sub(r"\\[a-zA-Z]+\*?(\[[^\]]*\])?(\{[^}]*\})?", " ", text)
text = re.sub(r"[{}$\\]", " ", text)
text = re.sub(r"~", " ", text)
text = re.sub(r"\s+", " ", text)
sents = re.split(r"(?<=[.!?])\s+(?=[A-Z(])", text)
sents = [s.strip() for s in sents if len(s.split()) >= 4]
sents = [s for s in sents if s.count(" & ") < 2]
print("prose sentences:", len(sents))
ws = [len(s.split()) for s in sents]
print("mean", round(statistics.mean(ws), 1), "median", statistics.median(ws))
print(">=50w:", sum(1 for w in ws if w >= 50),
      " >=60w:", sum(1 for w in ws if w >= 60),
      " >=70w:", sum(1 for w in ws if w >= 70))
for s in sorted(sents, key=lambda x: -len(x.split()))[:14]:
    print("\n[%dw] %s" % (len(s.split()), s))
