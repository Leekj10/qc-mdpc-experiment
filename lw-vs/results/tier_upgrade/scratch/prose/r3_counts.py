#!/usr/bin/env python3
"""Reviewer-3 scratch: count abstract/contribution lengths. Read-only on snapshots."""
import re
import sys

def strip_tex(s):
    s = re.sub(r"\\[a-zA-Z]+\*?(\[[^\]]*\])?", " ", s)   # commands
    s = re.sub(r"[{}~$\\]", " ", s)
    return s

for f in sys.argv[1:]:
    t = open(f, encoding="utf-8").read()
    m = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", t, re.S)
    ab = strip_tex(m.group(1))
    if "zh" in f:
        print(f, "abstract CJK chars:", len(re.findall(r"[\u4e00-\u9fff]", ab)))
    else:
        words = re.findall(r"[A-Za-z][A-Za-z0-9\-\.]*", ab)
        print(f, "abstract approx words:", len(words))
        # sentence count
        print("  sentences:", len(re.findall(r"[.!?](?:\s|$)", ab)))
    m2 = re.search(r"We make three contributions\.(.*?)\n", t, re.S)
    if m2:
        print("  EN contrib para words:", len(re.findall(r"[A-Za-z][A-Za-z0-9\-\.]*", strip_tex(m2.group(0)))))
        print("  EN contrib para sentences:", len(re.findall(r"[.!?](?:\s|$)", strip_tex(m2.group(0)))))
    m3 = re.search(r"本文的贡献有三。(.*?)\n", t, re.S)
    if m3:
        print("  ZH contrib para CJK chars:", len(re.findall(r"[\u4e00-\u9fff]", m3.group(0))))
        print("  ZH contrib para sentence stops:", len(re.findall(r"[。？！]", m3.group(0))))
