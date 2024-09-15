import sys, os, re, unicodedata
from tools.mediawiki import DB

PAGE = "পাতা"
NUMS = "০১২৩৪৫৬৭৮৯"

def bnnum(n):
    return "".join(NUMS[int(ch)] for ch in str(n))

args = sys.argv[1:]
if len(args) != 5:
    print(f"usage: python {sys.argv[0]} db index title out-dir pages-dir", file=sys.stderr)
    sys.exit(1)

db_file, index_file, title, out_dir, pages_dir = args
db = DB(db_file)
pdf = ""

with open(index_file, "r", encoding="utf_8") as f:
    chapter = 0
    for line in f:
        if m := re.match(r"\{\{Table\| title=\[\[/(.+?)/", line):
            chapter += 1
            p = title + "/" + m.group(1)
            if not (page := db[p]):
                print(f"not found: [{chapter}]", p, file=sys.stderr)
                continue
            if not pdf and (m := re.search(r'index="(.+?)"', page.text)):
                pdf = m.group(1)
            with open(os.path.join(out_dir, f"{chapter:02}.mw"), "wb") as f:
                f.write(page.text.encode("utf_8"))

if not pdf:
    print("PDF not found.", file=sys.stderr)
    sys.exit(1)

for p in range(1, 1000):
    if page := db[f"{PAGE}:{pdf}/{bnnum(p)}"]:
        with open(os.path.join(pages_dir, f"{p:03}.mw"), "wb") as f:
            f.write(page.text.encode("utf_8"))
    else:
        break
