import sys, re, common

args = sys.argv[1:]
if len(args) < 2:
    print(f"usage: python {sys.argv[0]} fix target1 [target2 ...]", file=sys.stderr)
    sys.exit(1)

fixes = common.read_fixes(args.pop(0))
for arg in args:
    fix = 0
    qs = []
    ignore = ""
    for q in common.read_queries(arg):
        if ignore:
            if q.info.startswith(ignore):
                continue
            else:
                ignore = ""
        info = q.info
        if m := re.search(r"\+\d$", info):
            info = info[:-2]
        if info in fixes:
            fix += 1
            qs += fixes.pop(q.info)
            if m:
                ignore = info
        else:
            qs.append(q)
    if fix:
        print("fixed:", arg, fix, "/", len(qs), file=sys.stderr)
        common.write_queries(arg, qs, count=len(qs))
if fixes:
    print("unfixed:", arg, len(fixes), list(fixes), file=sys.stderr)
