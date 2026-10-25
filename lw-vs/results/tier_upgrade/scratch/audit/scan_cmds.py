import re
from collections import Counter

BS = chr(92)
pat = re.compile(BS + BS + r"?[A-Za-z]+")

for f in [r"d:/桌面/TOUGAO - c/lw-vs/results/tier_upgrade/REPORT.md",
          r"d:/桌面/TOUGAO - c/lw-vs/results/tier_upgrade/paper_patch_draft.md"]:
    txt = open(f, encoding="utf-8").read()
    toks = re.findall(BS + r"[A-Za-z]+", txt)
    print(f)
    print("   tokens:", sorted(Counter(toks).items()))
    # show context of each backslash occurrence
    for m in re.finditer(BS + r".{0,25}", txt):
        pass
    idx = 0
    cnt = 0
    while True:
        i = txt.find(BS, idx)
        if i < 0:
            break
        cnt += 1
        print("   ctx:", repr(txt[max(0, i-25):i+25]))
        idx = i + 1
    print("   total backslashes:", cnt)
