import sys, os, re, xml7shi

def escape(s):
    return s.replace("<", "&lt;").replace(">", "&gt;").replace("&", "&amp;")

class query:
    def __init__(self):
        self.prompt = None
        self.info   = None
        self.result = None
        self.error  = None
        self.retry  = False

    def __str__(self):
        s = "<query>\n"
        if self.info:
            s += f"<info>{escape(self.info)}</info>\n"
        attrs = ' retry="true"' if self.retry else ''
        s += f"<prompt{attrs}>\n{escape(self.prompt)}\n</prompt>\n"
        if self.error:
            attrs = ' result="true"' if self.result else ''
            s += f"<error{attrs}>\n{escape(self.error)}\n</error>\n"
        if self.result:
            s += f"<result>\n{escape(self.result)}\n</result>\n"
        return s + "</query>\n"

def parse(xr: xml7shi.reader):
    q = query()
    while xr.read():
        if xr.tag == "prompt":
            q.retry = xr.get("retry") == "true"
            if xr.read():
                q.prompt = xr.text.strip()
        elif xr.tag == "info" and xr.read():
            q.info = xr.text.strip()
        elif xr.tag == "error" and xr.read():
            q.error = xr.text.strip()
        elif xr.tag == "result" and xr.read():
            q.result = xr.text.strip()
        elif xr.tag == "/query":
            break
    return q

def read_queries(file):
    with open(file, "r", encoding="utf-8") as f:
        xml = f.read()
    xr = xml7shi.reader(xml)
    qs = []
    while xr.read():
        if xr.tag == "query":
            qs.append(parse(xr))
    return qs

def write(f, text="", end="\n"):
    f.write((str(text) + end).encode("utf_8"))

def write_queries(file, qs, **root_attrs):
    with open(file, "wb") as f:
        write(f, xml7shi.declaration)
        attrs = "".join(f' {k}="{v}"' for k, v in root_attrs.items())
        write(f, f"<queries{attrs}>")
        for q in qs:
            write(f, q, end="")
        write(f, "</queries>")

def unzip(qs):
    ret = []
    for q in qs:
        ret.append(q.prompt)
        ret.append(q.result)
    return ret

# table

def read_table(src):
    ret = []
    for line in src.split("\n"):
        if line.startswith("|"):
            ret.append([t.strip() for t in line.split("|")[1:-1]])
        elif ret:
            break
    if len(ret) > 1 and not re.match(r"-+$", ret[1][0]):
        ret.insert(1, ["---"] * len(ret[0]))
    return ret

abbrevs = {
    "singular": "sg.", "plural": "pl.",
    "masculine": "m.", "feminine": "f.", "neuter": "n.",
    "first": "1", "second": "2", "third": "3",
    "1st": "1", "2nd": "2", "3rd": "3",
}

def fix_cell(cell):
    cell = cell.strip()
    if cell in ["-", "n/a", "N/A"]:
        return ""
    ab = abbrevs.get(cell.lower())
    if ab:
        return ab
    return cell

def fix_table(lines):
    output = ""
    for line in lines.split("\n"):
        if line.endswith("\r"):
            line = line[:-1]
        if line.startswith("|"):
            data = [fix_cell(cell) for cell in line.split("|")]
            line = "|".join(data)
        output += line + "\n"
    return output.rstrip()

# source

def read_source(path, language=None):
    srcs = []
    src_lines = {}

    file = path
    if path.endswith(".txt") or os.path.exists(file := f"{path}.txt"):
        with open(file, "r", encoding="utf-8") as f:
            ln = 1
            lines = []
            for line in f:
                line = line.strip()
                if line:
                    line = f"{ln} {line}"
                    src_lines[ln] = line
                    ln += 1
                    lines.append(line)
                    if len(lines) == 3:
                        srcs.append(lines)
                        lines = []
            if lines:
                srcs.append(lines)
        return srcs, src_lines

    file = path
    if path.endswith(".xml") or os.path.exists(file := f"{path}.xml"):
        qs = read_queries(file)
        if qs and (m := re.search(r"/(\d+)", qs[0].info)):
            src_lines = {int(m.group(1)): None}
        for q in qs:
            if not q.result:
                continue
            r = q.result
            if language and language in r:
                r = r[r.find("\n", r.find(language)):]
            lines = []
            for line in (r.strip() + "\n").split("\n"):
                if m := re.match(r"(\d+)", line):
                    src_lines[int(m.group(1))] = line
                if line:
                    lines.append(line)
                if lines and (len(lines) == 3 or not line):
                    srcs.append(lines)
                    lines = []
    else:
        print(f"no source files found in {path}", file=sys.stderr)
    return srcs, src_lines

# fix

def read_fixes(*fix_files):
    ret = {}
    for f in fix_files:
        for q in read_queries(f):
            info = q.info
            if re.search(r"\+\d$", info):
                info = info[:-2]
            if info not in ret:
                ret[info] = []
            ret[info].append(q)
    return ret

# Makefile

def read_defs(mk):
    ret = {}
    with open(mk, "r", encoding="utf-8") as f:
        for line in f:
            if m := re.match(r"(\w+)\s*=\s*(.+)", line):
                ret[m.group(1)] = m.group(2)
    return ret

# unify

def fix_length(lst, info, title):
    first = True
    length = len(lst[0])
    for i in lst[1:]:
        if length != len(i):
            if first:
                # print(f"{info} | length mismatch ({title}): {length} {lst[0]}", file=sys.stderr)
                first = False
            # print(f"    {len(i)} {i}", file=sys.stderr)
            while length > len(i):
                i.append("")

def read_tables(word, word_tr, etymology, index=0):
    qs0 = read_queries(word)
    qs1 = read_queries(word_tr)
    qs2 = read_queries(etymology) if os.path.exists(etymology) else None
    qi1 = {q.info: q for q in qs1}
    qi2 = {q.info: q for q in qs2} if qs2 else None
    for q0 in qs0:
        if not q0.result:
            continue
        q1 = qi1.get(q0.info)
        if not q1 or not q1.result:
            continue
        q2 = qi2.get(q0.info) if qi2 else None
        if qi2 and (not q2 or not q2.result):
            continue
        if not (m := re.search(r"columns (\d+)", q1.prompt)):
            print("no columns count:", q0.info, file=sys.stderr)
            continue
        col = int(m.group(1)) - 1
        ts0 = read_table(q0.result)
        tsp = read_table(q1.prompt)
        ts1 = read_table(q1.result)
        ts2 = read_table(q2.result) if q2 else None
        if len(ts0) == 0 or len(ts1) == 0:
            print(q0.info, "| empty table (error):", len(ts0), len(ts1), file=sys.stderr)
            continue
        fix_length(ts0, q0.info, "word")
        fix_length(tsp, q1.info, "word-tr.prompt")
        fix_length(ts1, q1.info, "word-tr")
        fix_length(ts2, q2.info, "etymology") if ts2 else None
        length = len(ts1)
        # if length != len(tsp):
        #     print(q0.info, "(word-tr) | length mismatch:", len(tsp), "!=", length, file=sys.stderr)
        if ts2 and length != len(ts2):
            print(q0.info, "(etymology) | length mismatch (error):", length, "!=", len(ts2), file=sys.stderr)
            continue
        table = []
        for i, r0 in enumerate(ts0):
            r = len(table)
            if r >= length:
                break
            if i > 1 and r0[index] != tsp[r][0]:
                # print(q0.info, "| word mismatch:", r0[index], "!=", tsp[r][0], file=sys.stderr)
                continue
            row = r0 + ts1[r][col:]
            if ts2:
                row += ts2[r][-2:]
            table.append(row)
        if length != len(table):
            words = " ".join(r[0] for r in tsp[len(table):])
            print(q0.info, "| unused words (error):", words, file=sys.stderr)
            continue
        lines = [line for line in q0.prompt.split("\n")[1:] if line]
        yield q0.info, lines, table

def split_table(info, lines, table):
    ret = [[] for _ in lines]
    data = table[1:]
    if data[0][0].startswith("---"):
        data = data[1:]
    ln = 0
    start = 0
    for rows in data:
        w = rows[0]
        bak = ln, start
        i = -1
        if len(lines[ln]) - start < len(w):
            ln += 1
            start = 0
        if ln == len(lines):
            left = ""
        else:
            left = " " + repr(lines[ln][start:])
            while i < 0:
                i = lines[ln].find(w, start)
                if i < 0:
                    start = 0
                    ln += 1
                    if ln == len(lines):
                        break
                else:
                    start = i + len(w)
        if i < 0:
            print(f"{info} | word not found: {w}{left}", file=sys.stderr)
            ln, start = bak
        ret[ln].append(rows)
    return ret

def write_md(line, header, table):
    ret = line + "\n\n"
    ret += "<table>\n"
    for i, h in enumerate(header):
        cells = [row[i] for row in table]
        if sum(map(len, cells)) == 0:
            continue
        row = "".join(f"<td>{td}</td>" for td in cells)
        if h == "Etymology":
            row = row.replace("<td>*", "<td><sup>*</sup>").replace("*</td>", "</td>")
        ret += f"<tr><th>{h}</th>{row}</tr>\n"
    ret += "</table>\n"
    return ret
