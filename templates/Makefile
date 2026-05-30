.DEFAULT: all

CHEETAH := $(shell command -v cheetah3 2>/dev/null)

%.py : %.tmpl
	$(CHEETAH) compile $<

TEMPLATES = \
	home.tmpl \

DEST_PY = $(TEMPLATES:.tmpl=.py)
all : $(DEST_PY)

clean :
	rm -f $(DEST_PY) *.py.bak
