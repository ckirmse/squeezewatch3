#!/usr/bin/python

from RequestLogic import RequestLogic

from SqueezeWatchApp import app

class zoneLogic(RequestLogic) :

	def get_context(self) :
		if not self.path_parameters :
			return {}
		zone_id = int(self.path_parameters[0])
		if not app.nuvo_protocol.isValidZone(zone_id) :
			return {}
		zone = app.nuvo_protocol.getZone(zone_id)
		return {
			'zone_id'   : zone_id,
			'zone_name' : zone.name,
		}
