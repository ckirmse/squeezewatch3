#!/usr/bin/python

import asyncio
import json

import aiohttp

from Log import *

# names shown as the title when the wiim reports a mode with no track metadata
wiim_mode_names = {
	1: 'AirPlay',
	2: 'DLNA',
	31: 'Spotify Connect',
	32: 'TIDAL Connect',
	40: 'Aux In',
	41: 'Bluetooth',
	42: 'External Storage',
	43: 'Optical In',
	50: 'Mirror',
	60: 'Voice Mail',
	99: 'Slave',
}

POLL_INTERVAL_SECONDS = 1
REQUEST_TIMEOUT_SECONDS = 3

class WiiMProtocol :

	def __init__(self,source,host) :
		self.source = source
		self.host = host
		self.poll_task = None
		self.was_reachable = True
		self.last_vendor = None
		self.last_position_seconds = None
		# the wiim uses a self-signed certificate, so verification is disabled
		self.session = aiohttp.ClientSession(
			connector=aiohttp.TCPConnector(ssl=False),
			timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT_SECONDS),
		)

	def setHost(self,host) :
		if host != self.host :
			log("wiim source",self.source,"host changed to",host)
			self.host = host

	def setActive(self,active) :
		if active :
			if self.poll_task is None :
				dlog("starting wiim polling for source",self.source)
				self.poll_task = asyncio.get_event_loop().create_task(self._pollLoop())
		else :
			if self.poll_task is not None :
				dlog("stopping wiim polling for source",self.source)
				self.poll_task.cancel()
				self.poll_task = None

	async def _fetchCommand(self,command) :
		url = 'https://' + self.host + '/httpapi.asp?command=' + command
		try :
			async with self.session.get(url) as response :
				text = await response.text()
		except (aiohttp.ClientError, asyncio.TimeoutError) as error :
			if self.was_reachable :
				elog("wiim source",self.source,"unreachable at",self.host,":",error)
				self.was_reachable = False
			return None
		if not self.was_reachable :
			log("wiim source",self.source,"reachable again at",self.host)
			self.was_reachable = True
		try :
			return json.loads(text)
		except ValueError :
			# some commands (e.g. setPlayerCmd) just return 'OK'
			return text

	async def refreshStatus(self) :
		# returns the live playback mode ('play'/'pause'/'stop'), or None if unreachable
		player_status = await self._fetchCommand('getPlayerStatus')
		if not isinstance(player_status, dict) :
			return None
		self.last_vendor = player_status.get('vendor', '')
		status = player_status.get('status', '')
		if status == 'play' :
			return 'play'
		if status == 'pause' :
			return 'pause'
		return 'stop'

	async def _pollLoop(self) :
		from SqueezeWatchApp import app
		while True :
			try :
				player_status = await self._fetchCommand('getPlayerStatus')
				meta_info = await self._fetchCommand('getMetaInfo')
				if isinstance(player_status, dict) :
					self.last_vendor = player_status.get('vendor', '')
					data = self._buildStatusData(player_status, meta_info)
					app.nuvo_protocol.answerStatus(self.source, data)
			except asyncio.CancelledError :
				raise
			except Exception as error :
				elog("wiim source",self.source,"poll loop error, continuing:",error)
			await asyncio.sleep(POLL_INTERVAL_SECONDS)

	def _safeInt(self,value,default=0) :
		try :
			return int(value)
		except (TypeError, ValueError) :
			return default

	def _buildStatusData(self,player_status,meta_info) :
		data = {}

		status = player_status.get('status', 'stop')
		if status == 'play' :
			data['mode'] = 'play'
		elif status == 'pause' :
			data['mode'] = 'pause'
		else :
			# 'stop' and 'loading'
			data['mode'] = 'stop'

		total_length_ms = self._safeInt(player_status.get('totlen', '0'))
		current_position_ms = self._safeInt(player_status.get('curpos', '0'))
		data['duration'] = str(total_length_ms / 1000)
		data['time'] = str(current_position_ms / 1000)
		self.last_position_seconds = current_position_ms / 1000

		loop_mode = self._safeInt(player_status.get('loop', '4'), default=4)
		if loop_mode in (0, 1, 2) :
			data['playlist repeat'] = '1'
		else :
			data['playlist repeat'] = '0'
		if loop_mode in (2, 3) :
			data['playlist shuffle'] = '1'
		else :
			data['playlist shuffle'] = '0'

		playlist_count = self._safeInt(player_status.get('plicount', '0'))
		playlist_current = self._safeInt(player_status.get('plicurr', '0'))
		if playlist_count > 0 :
			data['playlist_tracks'] = str(playlist_count)
			data['playlist_cur_index'] = str(playlist_current - 1)

		title = ''
		artist = ''
		album = ''
		artwork_url = ''
		if isinstance(meta_info, dict) and 'metaData' in meta_info :
			meta_data = meta_info['metaData']
			title = meta_data.get('title', '')
			artist = meta_data.get('artist', '')
			album = meta_data.get('album', '')
			artwork_url = meta_data.get('albumArtURI', '')
		if not title :
			mode_number = self._safeInt(player_status.get('mode', '0'))
			if mode_number in wiim_mode_names :
				title = wiim_mode_names[mode_number]
		data['title'] = title
		data['artist'] = artist
		data['album'] = album
		data['artwork_url'] = artwork_url

		return data

	def isSqueezeMode(self) :
		return self.last_vendor == 'squeezelite'

	def _sendCommand(self,command) :
		asyncio.get_event_loop().create_task(self._fetchCommand(command))

	def playPause(self) :
		self._sendCommand('setPlayerCmd:onepause')

	def pause(self) :
		self._sendCommand('setPlayerCmd:pause')

	def prevTrack(self) :
		self._sendCommand('setPlayerCmd:prev')

	def nextTrack(self) :
		self._sendCommand('setPlayerCmd:next')

	def setVolume(self,volume) :
		self._sendCommand('setPlayerCmd:vol:' + str(volume))

	def seek(self,seconds) :
		from SqueezeWatchApp import app
		target_seconds = int(seconds)
		self._sendCommand('setPlayerCmd:seek:' + str(target_seconds))
		# optimistically record the target so relative seeks compound correctly
		# and the web api reports the new position before the next poll
		self.last_position_seconds = target_seconds
		app.nuvo_protocol.updateSourcePosition(self.source, target_seconds)

	def seekOffset(self,offset) :
		if self.last_position_seconds is None :
			dlog("no known position for wiim source",self.source,"; cannot seek by offset")
			return
		target_seconds = self.last_position_seconds + offset
		if target_seconds < 0 :
			target_seconds = 0
		self.seek(target_seconds)
