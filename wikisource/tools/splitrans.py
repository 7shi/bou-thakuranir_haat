import sys

def split_block(filename):
    block = ""
    with open(filename, "r", encoding="utf_8") as f:
        for line in f:
            line = line.rstrip()
            if line:
                block += line + "\n"
            elif block:
                yield block
                block = ""
        if block:
            yield block

def split_file_line(filename, split_size=0):
    block = ""
    for b in split_block(filename):
        if split_size < 1 or len(block) + len(b) < split_size:
            if block:
                block += "\n"
            block += b
        elif block:
            yield block
            block = b
        else:
            yield b
            print("Warning: block too large", file=sys.stderr)
    if block:
        yield block

if __name__ == '__main__':
    import pyperclip

    args = sys.argv[1:]

    maximum = 0
    if len(args) >= 2 and args[0] == "-m":
        maximum = int(args[1])
        args = args[2:]

    if len(args) != 2:
        print(f"Usage: python {sys.argv[0]} [-m max] input output", file=sys.stderr)
        sys.exit()

    fin, fout = args
    result = ""
    blocks = list(split_file_line(fin, maximum))

    for i, block in enumerate(blocks):
        pyperclip.copy(block)
        print(f"[{i+1}/{len(blocks)}] Paste to the translator, copy the result.")
        t = pyperclip.waitForNewPaste()
        if result:
            result += '\n'
        result += t.rstrip().replace("\r\n", "\n") + "\n"

    with open(fout, "wb") as f:
        f.write(result.encode("utf_8"))
