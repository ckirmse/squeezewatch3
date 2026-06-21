#!/usr/bin/python

from Log import *

from RequestLogic import RequestLogic

from SqueezeWatchApp import app

class homeLogic(RequestLogic) :

	def get_context(self) :
		zones = app.nuvo_protocol.getZones()
		return {
			'zones' : [
				{
					'id'     : zone_id,
					'name'   : zone.name,
					'is_on'  : zone.isOn(),
					'source' : zone.getSource(),
				}
				for zone_id,zone in zones.items()
			]
		}
