#!/usr/bin/env python
"""Scratch analysis 2: classify self-limiting sentences and list long sentences.
Read-only: takes tex path as argv[1]."""
import re
import sys

path = sys.argv[1]
with open(path, encoding="utf-8") as f:
    raw = f.read()

text = re.sub(r"(?<!\\)%.*", " ", raw)
text = text.split("\\begin{document}", 1)[-1]
for env in ["figure*", "figure", "table*", "table", "equation", "equation*",
            "align", "align*", "algorithm", "algorithmic", "tabular",
            "IEEEkeywords", "abstract", "itemize", "enumerate"]:
    text = re.sub(r"\\begin\{%s\}(?:\{.*?\}|\[.*?\])?" % re.escape(env), " ", text)
    text = re.sub(r"\\end\{%s\}" % re.escape(env), " ", text)
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
text = text.replace("``", '"').replace("''", '"')

sents = re.split(r"(?<=[.!?])\s+(?=[A-Z(])", text)
sents = [s.strip() for s in sents if len(s.split()) >= 4]

# Self-limiting classes
classes = {
    "explicit-no-claim/prove/establish": r"\b(do(es)? not (prove|establish|demonstrate|claim|negate|verify)|not proven?|not established|not claimed|none is claimed|no evidence|not evidence|cannot demonstrate|does not by itself)\b",
    "unresolved/underpowered/exploratory": r"\b(unresolved|not resolved|not statistically resolved|underpowered|exploratory|prototype|not measurable|no failure is measurable)\b",
    "scope/limit nouns": r"\b(limitation|caveat|bounds? (what|every)|scope boundary|not a universal|not the strongest|not dominance|not a DFR theorem|far above|out of reach|beyond)\b",
    "rather than": r"rather than",
    "mid-sentence 'must not/need not'": r"\b(must not|need not|should not|may not)\b",
    "negated identity 'is not a/an/the'": r"\b(is|are) not (a|an|the) \b",
}
print(f"total sentences: {len(sents)}")
allhit = set()
for label, pat in classes.items():
    hits = [s for s in sents if re.search(pat, s, re.I)]
    print(f"{label}: {len(hits)}")
    for s in hits:
        pass
    for s in hits:
        allhit.add(s)
print(f"sentences with >=1 self-limiting marker (union): {len(allhit)} "
      f"({100*len(allhit)/len(sents):.1f}%)")

print("\n=== sentences >= 58 words ===")
for s in sorted(sents, key=lambda x: -len(x.split())):
    n = len(s.split())
    if n >= 58:
        print(f"\n[{n}w] {s}")

print("\n=== 'we'-subject sentence count ===")
we_start = [s for s in sents if re.match(r"^We\b", s)]
print(f"sentences starting with We: {len(we_start)}")
print(f"sentences containing 'we ' (any case-sensitive): {sum(1 for s in sents if re.search(r'\bwe\b', s))}")
