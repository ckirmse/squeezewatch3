#!/usr/bin/python

from Log import *

#from WebServApp import app

def renderTemplate(request,page,parameters,path_parameters,render_function) :

	template_class = None

	# check if file exists--if it does, puke on import error
	show_import_errors = True # app.config.get("system","show_import_errors")
	if show_import_errors :
		dlog("trying to import",page)
		mod = __import__(page)
		template_class = getattr(mod,page)
	else :
		try :
			mod = __import__(page)
			template_class = getattr(mod,page)
		except ImportError :
			pass
		except AttributeError :
			pass

	if template_class == None :
		from pageNotFound import pageNotFound as template_class
			
	template = template_class(request=request,page=page,parameters=parameters,
							  path_parameters=path_parameters)
	func = None
	if show_import_errors :
		func = getattr(template,render_function)
	else :
		try :
			func = getattr(template_class,render_function)
		except AttributeError :
			pass
		
	if not func :
		elog("function",render_function,"not implemented in page",template_class)
		request.setResponseCode(404)
		return ""

	# need to wrap with str() because it can't handle unicode
	s = str(func())

	return s

