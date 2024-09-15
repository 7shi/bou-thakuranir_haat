import sys, os, re, gemini.xml7shi as xml7shi

args = sys.argv[1:]
if not args:
    print(f"usage: python {sys.argv[0]} file1 [file2 ...]", file=sys.stderr)
    sys.exit(1)

tags = set()

def read_pages(xr):
    fp = int(xr["from"])
    fs = xr.get("fromsection")
    tp = int(xr["to"])
    ts = xr.get("tosection")
    text = ""
    for i in range(fp, tp + 1):
        with open(f"pages/{i:03}.mw", "r", encoding="utf_8") as f:
            mw = f.read()
        xr = xml7shi.reader(mw)
        sect = fs if i == fp else ts if i == tp else None
        if sect:
            if not xr.find("section", begin=sect):
                print(f"section not found: {i:03} {sect}", file=sys.stderr)
                xr = xml7shi.reader(mw)
        poem = False
        while xr.read():
            t = xr.text
            if poem:
                t = t.replace("\n", "\n\n")
            text += t
            if xr.tag == "noinclude":
                xr.find("/noinclude")
            elif xr.tag == "ref":
                xr.find("/ref")
            elif sect and xr.check("section", end=sect):
                break
            elif xr.tag == "poem":
                if not text.endswith("\n"):
                    text += "\n"
                text += "\n"
                poem = True
            elif xr.tag == "/poem":
                if not text.endswith("\n"):
                    text += "\n"
                text += "\n"
                poem = False
        if not text.endswith("\n"):
            text += "\n"
    text = text.replace("{{gap}}", "").replace("{{nop}}", "")
    text = re.sub(r"\{\{Custom rule\|.*?\}\}", "", text)
    ret = ""
    indent = 0
    h2 = True
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            if not ret.endswith("\n"):
                ret += "\n"
            continue
        if line == "{{block center/s}}":
            if not ret.endswith("\n"):
                ret += "\n"
            indent += 4
        elif line == "{{block center/e}}":
            if not ret.endswith("\n"):
                ret += "\n"
            indent -= 4
        elif line.startswith("{{C|") and line.endswith("}}"):
            line = line[4:-2]
            if not line:
                continue
            if m := re.match(r"\{\{xxxx-larger\|'''(.+?)'''", line):
                ret += "# " + m.group(1) + "\n"
            elif m := re.match(r"\{\{larger\|(.+)\}\}", line):
                if h2:
                    ret += "## "
                    h2 = False
                ret += m.group(1) + "\n"
            else:
                if not ret.endswith("\n"):
                    ret += "\n"
                ret += "    " + line + "\n"
        else:
            if m := re.match(r"\{\{Block center\|", line):
                if not ret.endswith("\n"):
                    ret += "\n"
                indent += 4
                line = line[m.end():]
            if indent and line.endswith("}}"):
                if line := line[:-2]:
                    line = " " * indent + line
                indent -= 4
            if not line:
                continue
            if m := re.match(r":+", line):
                e = m.end()
                line = " " * e + line[e:]
            if indent:
                line = " " * indent + line
            if not ret.endswith("\n"):
                ret += " "
            ret += line
    while (ps := ret.find("{{")) >= 0:
        i = 2
        pe = ps + 2
        while i and pe < len(ret):
            if ret[pe] == "{":
                i += 1
            elif ret[pe] == "}":
                i -= 1
            pe += 1
        s = ret[ps+2:pe-2]
        cols = s.split("|")
        tags.add(cols[0])
        ret = ret[:ps] + ret[pe:]
    return ret

for arg in args:
    print(arg, file=sys.stderr)
    with open(arg, "r", encoding="utf_8") as f:
        xr = xml7shi.reader(f.read())
    text = ""
    while xr.read():
        if xr.tag == "pages":
            text += read_pages(xr)
    md = os.path.splitext(arg)[0] + ".txt"
    with open(md, "wb") as f:
        f.write(text.encode("utf_8"))

print(tags)
