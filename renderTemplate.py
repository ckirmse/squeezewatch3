#!/usr/bin/python

from Log import *

def renderTemplate(request,page,parameters,path_parameters,render_function) :

	template_class = None

	try :
		mod = __import__(page)
		template_class = getattr(mod,page)
	except (ImportError, AttributeError) :
		dlog("page not found:",page)

	if template_class is None :
		return None

	template = template_class(request=request,page=page,parameters=parameters,
							  path_parameters=path_parameters)

	func = getattr(template,render_function,None)
	if not func :
		elog("function",render_function,"not implemented in page",template_class)
		return None

	s = str(func())

	return s.encode("utf-8")
