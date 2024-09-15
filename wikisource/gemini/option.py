import sys, os, re, common

args = sys.argv[1:]

directories = ["inferno", "purgatorio", "paradiso"]
init = "init.xml"
interval = 10
rangemax = 35
once  = False
retry = True
show  = True

def parse(f=None):
    global args, directories, init, interval, rangemax, once, retry, show, language, srcdir, outdir
    i = 0
    while i < len(args):
        length = len(args)
        if f:
            f(i, args)
        if len(args) != length:
            continue
        arg = args[i]
        if arg == "-d" and len(args) > i + 1:
            args.pop(i)
            directories = args.pop(i).split()
        elif arg == "-i" and len(args) > i + 1:
            args.pop(i)
            init = args.pop(i)
        elif arg == "-n" and len(args) > i + 1:
            args.pop(i)
            interval = int(args.pop(i))
        elif arg == "-r" and len(args) > i + 1:
            args.pop(i)
            rangemax = int(args.pop(i))
        elif arg == "-1":
            args.pop(i)
            once = True
        elif arg == "--no-retry":
            args.pop(i)
            retry = False
        elif arg == "--no-show":
            args.pop(i)
            show = False
        elif arg.startswith("-"):
            print(f"unknown option: {arg}", file=sys.stderr)
            return False
        else:
            i += 1
    if len(args) < 3:
        return False
    language = args.pop(0)
    srcdir = args.pop(0)
    outdir = args.pop(0)
    if not os.path.exists(outdir):
        os.mkdir(outdir)
    return True

def show():
    print("  -d dir: specify sub directory", file=sys.stderr)
    print("  -i file: specify init.xml", file=sys.stderr)
    print("  -n num: specify interval (default 10)", file=sys.stderr)
    print("  -r num: specify range (default 35)", file=sys.stderr)
    print("  -1: just do one canto", file=sys.stderr)
    print("  --no-retry: don't retry queries", file=sys.stderr)
    print("  --no-show: don't show queries and responses", file=sys.stderr)

def proc(f):
    global directory, canto, info
    for directory in directories:
        diru = directory[0].upper() + directory[1:]
        path_s = os.path.join(srcdir, directory)
        if not os.path.exists(path_s):
            continue
        path_o = os.path.join(outdir, directory)
        if not os.path.exists(path_o):
            os.mkdir(path_o)
        for canto in range(1, rangemax + 1):
            src = os.path.join(path_s, f"{canto:02}.xml")
            if not os.path.exists(src):
                src = src[:-3] + "txt"
            if not os.path.exists(src):
                break
            xml = os.path.join(path_o, f"{canto:02}.xml")
            if os.path.exists(xml):
                continue
            print()
            info = f"{diru} Canto {canto}"
            print("#", info)
            f(src, xml)
            if once:
                sys.exit(0)
