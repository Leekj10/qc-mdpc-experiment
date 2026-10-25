# -*- coding: utf-8 -*-
"""Novel-number scan, gate-equivalent acceptance.

A numeric token is accepted when:
  (a) it equals a layout/preamble value (pattern-based), or
  (b) it appears in a URL/DOI, or
  (c) some archive-derived value a satisfies: round(a * 10^k, p) == token,
      where p is the token's decimal precision and k any integer in [-24, 24]
      (this covers prose renderings like 1.32 meaning 1.32e-3, and correct
      rounded renderings such as 0.16 for 0.16153).
Only tokens failing all three are reported."""
import re
import sys
from pathlib import Path

BASE = Path(r"D:/桌面/TOUGAO - c/lw-vs/v3")
TOK = re.compile(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?")
LAYOUT = re.compile(r"p\{[0-9.]+cm\}|\{[0-9.]+(?:em|pt|cm|in)\}|fontsize\{[^}]*\}")
URL = re.compile(r"\\url\{[^}]*\}|doi\.org/\S+|zenodo\.\d+|github\.com/\S+")

allowed_vals = []
for tok in (BASE / "plan" / "allowed_numbers.txt").read_text(encoding="utf-8").split():
    try:
        allowed_vals.append(float(tok))
    except ValueError:
        pass


def accepted(tok: str) -> bool:
    tok = tok.replace(",", "")
    try:
        v = float(tok)
    except ValueError:
        return True
    dec = len(tok.split(".")[1]) if "." in tok else 0
    if dec == 0:
        dec_hi = 0
    for a in allowed_vals:
        for k in range(-24, 25):
            av = a * (10.0 ** k)
            if av == 0:
                continue
            if abs(av - v) <= 6e-3 * abs(v):        # gate tolerance
                return True
            if dec <= 6 and round(av, dec) == v:    # correct rounding to token precision
                return True
    return False


for rel in sys.argv[1:] or ["en/main.tex"]:
    t = (BASE / rel).read_text(encoding="utf-8")
    body = t[t.find(r"\begin{document}"):]
    body = LAYOUT.sub(" ", body)
    body = URL.sub(" ", body)
    novel = {}
    for m in TOK.finditer(body):
        tok = m.group(0)
        if tok.replace(",", "") in ("", ) :
            continue
        if not accepted(tok):
            s = max(0, m.start() - 55)
            novel.setdefault(tok, body[s:m.end() + 35].replace("\n", " "))
    print(f"==== {rel}: {len(novel)} genuinely novel tokens ====")
    for tok, ctx in novel.items():
        print(f"  {tok:14s} | ...{ctx}...")
