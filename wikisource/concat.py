import sys
from gemini.xml7shi import reader

# The Wikisource text writes the vowel sign O two ways: the single sign, and
# the pair AA + E (822 times), which renders almost alike but is a different
# string - enough to look like a spelling variant to anything comparing
# proper nouns. Three more spots carry a stray E after an O sign. Bengali
# puts at most one vowel sign on a consonant, so neither sequence can be
# legitimate. Normalized here rather than in chapters/*.txt, so that the
# translation XMLs stay a record of what was actually sent to the model while
# all/bn.md comes out clean on every regeneration.
VOWEL_FIXES = [("াে", "ো"), ("োে", "ো")]


def normalize(text):
    for legacy, fixed in VOWEL_FIXES:
        text = text.replace(legacy, fixed)
    return text


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
            print(normalize(text.rstrip().splitlines()[-1]))
