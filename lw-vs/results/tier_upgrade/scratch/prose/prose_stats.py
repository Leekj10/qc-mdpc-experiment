#!/usr/bin/env python
"""Scratch analysis: prose statistics for the lw-vs optimized manuscript.
Read-only: takes tex path as argv[1]. Does not modify any file."""
import re
import sys
import statistics

path = sys.argv[1]
with open(path, encoding="utf-8") as f:
    raw = f.read()

# Remove comments (but keep \% escapes)
text = re.sub(r"(?<!\\)%.*", " ", raw)
# Drop preamble up to \begin{document}
text = text.split("\\begin{document}", 1)[-1]
# Drop figure/table/equation/algorithm bodies (they are not prose sentences)
for env in ["figure*", "figure", "table*", "table", "equation", "equation*",
            "align", "align*", "algorithm", "algorithmic", "tabular", "IEEEkeywords",
            "abstract", "itemize", "enumerate"]:
    text = re.sub(r"\\begin\{%s\}(?:\{.*?\}|\[.*?\])?" % re.escape(env),
                  " ", text)
    text = re.sub(r"\\end\{%s\}" % re.escape(env), " ", text)

# Replace LaTeX constructs with plain-ish text
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

# Sentence split (rough): period/question/exclamation followed by space + capital
sents = re.split(r"(?<=[.!?])\s+(?=[A-Z(])", text)
sents = [s.strip() for s in sents if len(s.split()) >= 4]

words = [len(s.split()) for s in sents]
print(f"file: {path}")
print(f"n_sentences: {len(sents)}")
print(f"mean words/sentence: {statistics.mean(words):.1f}")
print(f"median: {statistics.median(words)}")
print(f"n>50w: {sum(1 for w in words if w > 50)}")
print(f"n>60w: {sum(1 for w in words if w > 60)}")
print(f"n>70w: {sum(1 for w in words if w > 70)}")

def show(label, pat):
    hits = [s for s in sents if re.search(pat, s, re.I)]
    print(f"\n### {label}: {len(hits)} sentences")
    for h in hits:
        print(f"  [{len(h.split())}w] {h[:400]}")

show("self-limiting-negation", r"\b(do(es)? not|did not|cannot|can not|never|not [a-z]+|no evidence|neither|none|unresolved|unproven|rather than)\b")
show("we-report-rather", r"we report.{0,80}rather than|rather than (present|treat|assum|claim)|reported rather than")
show("meta-commentary", r"we (state it that way|repeat|reran|flag that|take the|note that)|ships with|the archive|the project's|released package|earlier analysis|earlier design|pipeline check")
show("program-voice", r"we (make|use|define|adopt|add|ran|run|implement|report|show|find|stress|repeat|take)")
