#!/usr/bin/python

import json

from RequestLogic import RequestLogic

from SqueezeWatchApp import app

from zigutils import volumeToPercent

class playerLogic(RequestLogic) :

	def getContext(self) :
		nuvo_zones = app.nuvo_protocol.getZones()

		zones = []
		for zone_id in sorted(nuvo_zones.keys()) :
			zone = nuvo_zones[zone_id]
			zones.append({
				'id'     : zone_id,
				'name'   : zone.name,
				'is_on'  : zone.isOn(),
				'source' : zone.getSource(),
				'volume' : volumeToPercent(zone.getVolume()),
			})

		initial_zone_id = None

		if 'zone' in self.parameters :
			try :
				requested_zone_id = int(self.parameters['zone'][0])
			except ValueError :
				requested_zone_id = None
			if requested_zone_id is not None and app.nuvo_protocol.isValidZone(requested_zone_id) :
				initial_zone_id = requested_zone_id

		if initial_zone_id is None :
			for zone in zones :
				if zone['is_on'] :
					initial_zone_id = zone['id']
					break

		if initial_zone_id is None and zones :
			initial_zone_id = zones[0]['id']

		return {
			'zones_json'           : json.dumps(zones),
			'initial_zone_id_json' : json.dumps(initial_zone_id),
		}
