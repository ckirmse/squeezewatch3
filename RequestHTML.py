#!/usr/bin/python

import re

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response

from Log import *

from renderTemplate import renderTemplate

from SqueezeWatchApp import app as squeeze_app

http_app = FastAPI()

@http_app.get("/api/zone/{zone_id}/status")
async def zone_status(zone_id: int) :
	if not squeeze_app.nuvo_protocol.isValidZone(zone_id) :
		return JSONResponse(status_code=404, content={"error": "zone not found"})

	zone = squeeze_app.nuvo_protocol.getZone(zone_id)
	source = zone.getSource()

	lines = ["", "", "", ""]
	mode = "unknown"

	if source != 0 :
		display_lines = squeeze_app.nuvo_protocol.getDisplayLines(source)
		for i in range(4) :
			lines[i] = display_lines.get(i + 1, "")
		status = squeeze_app.nuvo_protocol.source_data[source]['playback_mode']
		if status == 0 :
			mode = "stop"
		elif status == 2 :
			mode = "play"
		elif status == 3 :
			mode = "pause"
		elif status is not None :
			mode = "play"

	return JSONResponse({
		"zone_id": zone_id,
		"zone_name": zone.name,
		"is_on": zone.isOn(),
		"source": source,
		"lines": lines,
		"mode": mode,
	})

@http_app.get("/api/zone/{zone_id}/favorites")
async def zone_favorites(zone_id: int) :
	result = await squeeze_app.getFavorites(0, 100)
	if not result :
		return JSONResponse({"favorites": []})
	favorites_data, = result
	return JSONResponse({
		"favorites": [{"id": favorite_id, "name": name} for favorite_id, name, url in favorites_data]
	})

@http_app.get("/api/zone/{zone_id}/action")
async def zone_action(zone_id: int, action: str = "", favorite_id: str = "") :
	if not squeeze_app.nuvo_protocol.isValidZone(zone_id) :
		return JSONResponse(status_code=404, content={"error": "zone not found"})

	zone = squeeze_app.nuvo_protocol.getZone(zone_id)
	source = zone.getSource()

	if action == "zone_on" :
		squeeze_app.nuvo_protocol.sendZoneOn(zone_id)
	elif action == "zone_off" :
		squeeze_app.nuvo_protocol.sendZoneOff(zone_id)
	elif source == 0 :
		return JSONResponse({"ok": False, "error": "zone is off"})
	elif action == "play_pause" :
		squeeze_app.playPause(source)
	elif action == "next_track" :
		squeeze_app.nextTrack(source)
	elif action == "prev_track" :
		squeeze_app.prevTrack(source)
	elif action == "play_favorite" :
		squeeze_app.playFavorite(source, favorite_id)

	return JSONResponse({"ok": True})

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

	result = renderTemplate(request, page, parameters, path_parameters)
	if result is None :
		return HTMLResponse(content="Not Found", status_code=404)
	return HTMLResponse(content=result.decode('utf-8'))
