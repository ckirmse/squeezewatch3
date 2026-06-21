#!/usr/bin/python

import re

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, Response

from Log import *

from renderTemplate import renderTemplate

from SqueezeWatchApp import app as squeeze_app

http_app = FastAPI()

@http_app.get("/{path:path}")
async def handle(request: Request, path: str) :

	parameters = {}
	for key in request.query_params.keys() :
		parameters[key] = request.query_params.getlist(key)

	if 'action' in parameters :
		if parameters["action"][0] == "zone_on" :
			zone_num = int(parameters["zone"][0])
			if squeeze_app.nuvo_protocol.isValidZone(zone_num) :
				squeeze_app.nuvo_protocol.sendZoneOn(zone_num)
		elif parameters["action"][0] == "zone_off" :
			zone_num = int(parameters["zone"][0])
			if squeeze_app.nuvo_protocol.isValidZone(zone_num) :
				squeeze_app.nuvo_protocol.sendZoneOff(zone_num)
		elif parameters["action"][0] == "all_off" :
			squeeze_app.nuvo_protocol.sendAllOff()

	raw_path = re.split("/", path)
	processed_path = [s for s in raw_path if s != '']

	if len(processed_path) == 0 :
		page = "home"
		path_parameters = []
	else :
		page = processed_path[0]
		path_parameters = processed_path[1:]

	if page == "favicon.ico" :
		return Response(content=b"", media_type="image/x-icon")

	dlog("render HTML page", page, "path parameters:", ".".join(path_parameters))

	result = renderTemplate(request, page, parameters, path_parameters, 'renderHTMLPage')
	if result is None :
		return HTMLResponse(content="Not Found", status_code=404)
	return HTMLResponse(content=result.decode('utf-8'))
