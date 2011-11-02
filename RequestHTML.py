#!/usr/bin/python

import re

from twisted.web.resource import Resource

from Log import *

#from renderTemplate import renderTemplate

from SqueezeWatchApp import app

class RequestHTML(Resource) :

	isLeaf = True

	def __init__(self,page) :
		self.page = page

	def render_GET(self,request) :

		request.setHeader("Content-Type","text/html")

		parameters = request.args

		raw_path = re.split("/",request.path)
		processed_path = [s for s in raw_path if s != '']

		zones = app.nuvo_protocol.getZones()
		strs = []
		for (zoneid,zone) in zones.iteritems() :
			strs.append("zone "+str(zone.getZoneID()) + "(" + zone.name + ")" + str(" : source ") + str(zone.getSource()) + "<br/>\n")
		return "".join(strs)

		#dlog("page is",self.page,"path is","/".join(processed_path))

		# if len(processed_path) == 0 :
		# 	page = "home"
		# 	path_parameters = []
		# else :
		# 	# need to cleanse page of non a-z
		# 	page = processed_path[0]
		# 	path_parameters = processed_path[1:]

		# dlog("render HTML page",page,"path parameters:",".".join(path_parameters))

		# return renderTemplate(ZigRequest(request),page,parameters,path_parameters,'renderHTMLPage')
