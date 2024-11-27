#!/usr/bin/python

from Log import *

from RequestLogic import RequestLogic

from SqueezeWatchApp import app

class homeLogic(RequestLogic) :

	def __init__(self,*args,**kw) :
		RequestLogic.__init__(self,*args,**kw)

	def zones(self) :
		return app.nuvo_protocol.getZones().keys()

	def zoneIsOn(self,zone_num) :
		zone = app.nuvo_protocol.getZone(zone_num)
		return zone.isOn()

	def zoneName(self,zone_num) :
		zone = app.nuvo_protocol.getZone(zone_num)
		return zone.name

	def source(self,zone_num) :
		zone = app.nuvo_protocol.getZone(zone_num)
		return zone.getSource()

	def state(self,zone_num) :
		zone = app.nuvo_protocol.getZone(zone_num)
		return zone.getState()

	def stateName(self,zone_num) :
		zone = app.nuvo_protocol.getZone(zone_num)
		return zone.getStateName()
