#!/usr/bin/python

import re

from twisted.web.resource import Resource

from Log import *

from renderTemplate import renderTemplate

from SqueezeWatchApp import app

class RequestHTML(Resource) :

	isLeaf = True

	def __init__(self,page) :
		self.page = page

	def render_GET(self,request) :

		request.setHeader("Content-Type","text/html")

		parameters = request.args
		#dlog(parameters)
		if 'action' in parameters :
			if parameters["action"][0] == "zone_on" :
				zone_num = int(parameters["zone"][0])
				if app.nuvo_protocol.isValidZone(zone_num) :
					app.nuvo_protocol.sendZoneOn(zone_num)
			elif parameters["action"][0] == "zone_off" :
				zone_num = int(parameters["zone"][0])
				if app.nuvo_protocol.isValidZone(zone_num) :
					app.nuvo_protocol.sendZoneOff(zone_num)
			elif parameters["action"][0] == "all_off" :
				app.nuvo_protocol.sendAllOff()


		raw_path = re.split("/",request.path)
		processed_path = [s for s in raw_path if s != '']

		zones = app.nuvo_protocol.getZones()
		strs = []
		for (zoneid,zone) in zones.items() :
			strs.append("zone "+str(zone.getZoneID()) + "(" + zone.name + ")" + " : ")
			if zone.isOn() :
				strs.append("source " + str(zone.getSource()))
				strs.append(" <a href=\"?action=zone_off&zone=" + str(zone.getZoneID()) + "\">Turn Off</a>")
			else :
				strs.append("<a href=\"?action=zone_on&zone=" + str(zone.getZoneID()) + "\">Turn On</a>")

			strs.append("<br/>\n")
		strs.append("<a href=\"?action=all_off\">All Off</a>")

		#return "".join(strs)

		#dlog("page is",self.page,"path is","/".join(processed_path))

		if len(processed_path) == 0 :
		 	page = "home"
		 	path_parameters = []
		else :
			# need to cleanse page of non a-z
			page = processed_path[0]
			path_parameters = processed_path[1:]

		if page == "favicon.ico" :
			return ""

		#dlog("render HTML page",page,"path parameters:",".".join(path_parameters))

		return renderTemplate(request,page,parameters,path_parameters,'renderHTMLPage')
