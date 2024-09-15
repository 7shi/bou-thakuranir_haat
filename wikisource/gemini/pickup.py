import sys, common

args = sys.argv[1:]

check_table = False
if args and args[0] == "-t":
    check_table = True
    args.pop(0)

if len(args) < 2:
    print(f"Usage: python {sys.argv[0]} [-t] output file1 [file2 ...]", file=sys.stderr)
    sys.exit(1)

output = args.pop(0)

whole = 0
queries = []
for f in args:
    for q in common.read_queries(f):
        whole += 1
        if check_table:
            if q.result:
                if "||---" in q.result or not common.read_table(q.result):
                    queries.append(q)
        elif not q.result:
            queries.append(q)

print(f"error {len(queries)}/{whole}", file=sys.stderr)
common.write_queries(output, queries, count=len(queries), whole=whole)
