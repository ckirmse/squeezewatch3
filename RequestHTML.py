#!/usr/bin/python

import re
import time

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

from Log import *

from renderTemplate import renderTemplate

from SqueezeWatchApp import app as squeeze_app

http_app = FastAPI()

def volume_to_percent(volume) :
    if volume is None :
        return None
    return round((79 - volume) / 79 * 100)

@http_app.get("/api/zone/{zone_id}/status")
async def zone_status(zone_id: int) :
	if not squeeze_app.nuvo_protocol.isValidZone(zone_id) :
		return JSONResponse(status_code=404, content={"error": "zone not found"})

	zone = squeeze_app.nuvo_protocol.getZone(zone_id)
	source = zone.getSource()

	lines = ["", "", "", ""]
	mode = "unknown"
	duration_sec = None
	position_sec = None
	position_age_sec = None

	is_known_source = source in squeeze_app.nuvo_protocol.source_data

	if source != 0 and is_known_source :
		display_lines = squeeze_app.nuvo_protocol.getDisplayLines(source)
		for i in range(4) :
			lines[i] = display_lines.get(i + 1, "")
		status = squeeze_app.nuvo_protocol.source_data[source]['playback_mode']
		if status is None :
			status = squeeze_app.nuvo_protocol.getDisplayStatus(source)
		if status == 0 :
			mode = "stop"
		elif status == 2 :
			mode = "play"
		elif status == 3 :
			mode = "pause"
		elif status is not None :
			mode = "play"

		duration_sec = squeeze_app.nuvo_protocol.source_data[source]['duration_sec']
		position_sec = squeeze_app.nuvo_protocol.source_data[source]['position_sec']
		position_timestamp = squeeze_app.nuvo_protocol.source_data[source]['position_timestamp']
		if position_timestamp is not None :
			position_age_sec = time.time() - position_timestamp

	artwork_url = ''
	if source != 0 and is_known_source :
		lms_artwork_url = squeeze_app.nuvo_protocol.source_data[source].get('artwork_url', '')
		if lms_artwork_url :
			if lms_artwork_url.startswith('/') :
				artwork_url = squeeze_app.lms_http_base_url + lms_artwork_url
			else :
				artwork_url = lms_artwork_url
		else :
			coverid = squeeze_app.nuvo_protocol.source_data[source].get('coverid', '')
			if coverid :
				artwork_url = '/api/artwork/' + coverid

	return JSONResponse({
		"zone_id": zone_id,
		"zone_name": zone.name,
		"is_on": zone.isOn(),
		"source": source,
		"volume": volume_to_percent(zone.getVolume()),
		"lines": lines,
		"mode": mode,
		"artwork_url": artwork_url,
		"duration_sec": duration_sec,
		"position_sec": position_sec,
		"position_age_sec": position_age_sec,
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

@http_app.get("/api/zone/{zone_id}/volume")
async def zone_set_volume(zone_id: int, percent: int) :
    if not squeeze_app.nuvo_protocol.isValidZone(zone_id) :
        return JSONResponse(status_code=404, content={"error": "zone not found"})
    percent = max(0, min(100, percent))
    nuvo_volume = round(79 - (percent / 100 * 79))
    squeeze_app.nuvo_protocol.sendZoneVolume(zone_id, nuvo_volume)
    return JSONResponse({"ok": True, "volume": percent})

@http_app.get("/api/zone/{zone_id}/action")
async def zone_action(zone_id: int, action: str = "", favorite_id: str = "", source_id: int = 0) :
	if not squeeze_app.nuvo_protocol.isValidZone(zone_id) :
		return JSONResponse(status_code=404, content={"error": "zone not found"})

	zone = squeeze_app.nuvo_protocol.getZone(zone_id)
	source = zone.getSource()

	if action == "zone_on" :
		squeeze_app.nuvo_protocol.sendZoneOn(zone_id)
	elif action == "zone_off" :
		squeeze_app.nuvo_protocol.sendZoneOff(zone_id)
	elif action == "set_source" :
		if source_id :
			squeeze_app.nuvo_protocol.sendZoneSource(zone_id, source_id)
	elif action == "volume_up" :
		squeeze_app.nuvo_protocol.sendZoneVolumeUp(zone_id)
	elif action == "volume_down" :
		squeeze_app.nuvo_protocol.sendZoneVolumeDown(zone_id)
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

@http_app.get("/api/zones")
async def zones() :
	nuvo_zones = squeeze_app.nuvo_protocol.getZones()
	result = []
	for zone_id in sorted(nuvo_zones.keys()) :
		zone = nuvo_zones[zone_id]
		result.append({
			"id"     : zone_id,
			"name"   : zone.name,
			"is_on"  : zone.isOn(),
			"source" : zone.getSource(),
			"volume" : volume_to_percent(zone.getVolume()),
		})
	return JSONResponse({"zones": result})

@http_app.get("/api/sources")
async def sources() :
	source_names = squeeze_app.nuvo_protocol.getSourceNames()
	result = []
	for source_id in sorted(source_names.keys()) :
		result.append({"id": source_id, "name": source_names[source_id]})
	return JSONResponse({"sources": result})

@http_app.get("/api/artwork/{coverid}")
async def artwork_proxy(coverid: str) :
	url = squeeze_app.lms_http_base_url + '/music/' + coverid + '/cover.jpg'
	return RedirectResponse(url)

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
