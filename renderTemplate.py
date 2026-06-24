#!/usr/bin/python

import jinja2

from Log import *

_env = jinja2.Environment(loader=jinja2.FileSystemLoader('templates'))

def renderTemplate(request,page,parameters,path_parameters) :

	try :
		mod = __import__(page + 'Logic')
		logic_class = getattr(mod,page + 'Logic')
	except (ImportError, AttributeError) :
		dlog("page not found:",page)
		return None

	logic = logic_class(request,page,parameters,path_parameters)

	try :
		template = _env.get_template(page + '.html')
	except jinja2.TemplateNotFound :
		dlog("template not found:",page)
		return None

	return template.render(**logic.getContext()).encode('utf-8')
