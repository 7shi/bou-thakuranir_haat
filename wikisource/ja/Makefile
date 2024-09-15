include ../common.mk

all: translate check

translate:
	mkdir -p chapters
	python ../gemini/translate.py -n 1 Japanese .. .

check:
	python ../gemini/pickup.py 1-error.xml $(XMLS)

archive:
	tar cvzf archive.tar.gz $(DIRS)

backup:
	for d in $(DIRS); do rm -rf $$d.orig; cp -r $$d $$d.orig; done

redo:
	python ../gemini/redo.py 1-error.xml

redo1:
	python ../gemini/redo.py -1 1-error.xml

replace: backup
	python ../gemini/replace.py 1-error-ok.xml $(XMLS)
