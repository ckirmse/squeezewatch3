#!/usr/bin/python

from Cheetah.Template import Template

from Log import *

class RequestLogic(Template) :

	def __init__(self,request,*args,**kw) :
		self.request = request

		Template.__init__(self)
