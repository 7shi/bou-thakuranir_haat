TARGET1 = bnwikisource
TARGET2 = 20240101
TARGET  = $(TARGET1)-$(TARGET2)-pages-articles-multistream.xml.bz2
TITLE   = "বৌ-ঠাকুরাণীর হাট"

all:

.PHONY: download db-make extract convert text

download:
	wget https://dumps.wikimedia.org/$(TARGET1)/$(TARGET2)/$(TARGET)

db-make: db-pages.tsv

db-pages.tsv: $(TARGET)
	python tools/db-make.py $(TARGET)

dump.db: db-pages.tsv
	sqlite3 $@ ".read tools/db.sql"

index.mw: dump.db
	python tools/mediawiki.py -o $@ $< $(TITLE)

extract: extract.py dump.db index.mw
	mkdir -p chapters pages
	python $^ $(TITLE) chapters pages

convert:
	python convert.py chapters/*.mw

text:
	python concat.py -p en/chapters/*.xml > ../all-bn.md
	python concat.py en/chapters/*.xml > ../all-en-gemini.md
	python concat.py hi/chapters/*.xml > ../all-hi-gemini.md
	python concat.py ja/chapters/*.xml > ../all-ja-gemini.md
