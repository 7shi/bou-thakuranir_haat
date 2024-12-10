import argparse
parser = argparse.ArgumentParser()
parser.add_argument("text", help="input text file")
parser.add_argument("-o", "--output", help="output text file", default="output.txt")
parser.add_argument("-t", "--type", help="select type (1, 2, 3)", type=int, choices=[1,2,3], default=3)
parser.add_argument("-l", "--lang", help="specify language", default="ja")
args = parser.parse_args()

with open(args.text, "r", encoding="utf-8") as f:
    lines = [line.rstrip() for line in f.readlines()]

if args.type == 2:
    if args.lang == "ja":
        from spacy.lang.ja import Japanese
        nlp = Japanese()
        nlp.add_pipe("sentencizer")
    else:
        from spacy.lang.en import English
        nlp = English()
        nlp.add_pipe("sentencizer")
else:
    import spacy
    nlp = spacy.load("ja_core_news_sm" if args.lang == "ja" else "en_core_web_sm")

with open(args.output, "w", encoding="utf-8") as f:
    from tqdm import tqdm
    for line in tqdm(lines):
        if not line or line.startswith("#"):
            print(line, file=f)
        else:
            sents = []
            for sent in nlp(line).sents:
                if args.lang == "ja" and args.type == 3 and sent.text == "」":
                    sents[-1] += sent.text
                else:
                    sents.append(sent.text)
            for sent in sents:
                print(sent, file=f)
