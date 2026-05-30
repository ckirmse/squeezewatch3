.DEFAULT: all

CHEETAH := $(shell command -v cheetah 2>/dev/null || echo $(HOME)/Library/Python/3.9/bin/cheetah)

%.py : %.tmpl
	$(CHEETAH) compile $<

TEMPLATES = \
	home.tmpl \

DEST_PY = $(TEMPLATES:.tmpl=.py)
all : $(DEST_PY)

clean :
	rm -f $(DEST_PY) *.py.bak
