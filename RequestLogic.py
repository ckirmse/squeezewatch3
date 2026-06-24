#!/usr/bin/python

from Log import *

class RequestLogic :

	def __init__(self,request,page,parameters,path_parameters) :
		self.request = request
		self.page = page
		self.parameters = parameters
		self.path_parameters = path_parameters

	def getContext(self) :
		return {}
