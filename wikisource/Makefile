TARGET1 = bnwikisource
TARGET2 = 20240101
TARGET  = $(TARGET1)-$(TARGET2)-pages-articles-multistream.xml.bz2
TITLE   = "বৌ-ঠাকুরাণীর হাট"

all:

.PHONY: download db-make extract convert

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
