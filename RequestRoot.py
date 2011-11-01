#!/usr/bin/python

import re

from twisted.web.resource import Resource

from Log import *

from RequestHTML import RequestHTML

from SqueezeWatchApp import app

class RequestRoot(Resource) :

	def getChild(self,page,request) :

		#app.request_store.addRequest(request)

		# render HTML page by default
		# should we look at user-agent to see if there's something better to do?
		# maybe special versions for web vs. a phone?

		return RequestHTML(page)
