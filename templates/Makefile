.DEFAULT: all

%.py : %.tmpl
	cheetah compile $<

TEMPLATES = \
	home.tmpl \

DEST_PY = $(TEMPLATES:.tmpl=.py)
all : $(DEST_PY)

clean :
	rm -f $(DEST_PY) *.py.bak
