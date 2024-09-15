import sys
from gemini.xml7shi import reader

args = sys.argv[1:]
prompt = False
if args and args[0] == "-p":
    prompt = True
    args = args[1:]

if len(args) == 0:
    print(f"Usage: python {sys.argv[0]} [-p] xml [...]", file=sys.stderr)
    sys.exit(1)

first = True
for xml in args:
    with open(xml) as f:
        xr = reader(f.read())
    while xr.read():
        text = ""
        if prompt:
            if xr.tag == "prompt" and xr.read():
                text = xr.text
        elif xr.tag == "result" and xr.read():
            text = xr.text
        if text:
            if first:
                first = False
            else:
                print()
            print(text.rstrip().splitlines()[-1])
