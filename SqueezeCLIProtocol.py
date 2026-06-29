#!/usr/bin/python

import asyncio
import re

from urllib.parse import unquote

from Log import *

from SqueezeWatchApp import app


class SqueezeCLIProtocol(asyncio.Protocol) :

	def __init__(self, factory) :
		self.factory = factory
		self.transport = None
		self._buf = b''
		self._disconnected = asyncio.Event()
		self.context_map = {}
		self.next_context = 1

	async def waitDisconnected(self) :
		await self._disconnected.wait()

	def connection_made(self, transport) :
		self.transport = transport
		self._disconnected.clear()
		dlog("connection made")
		self.factory.notifyConnectionMade(self)

		self.send("subscribe playlist,favorites,client,rescan")
		self.send("pref httpport ?")

		# get info on the players out there - should parse "client" messages to know when changed
		self.send("players 0 5")

	def connection_lost(self, exc) :
		dlog("connection lost")
		self.transport = None
		self._disconnected.set()

	def data_received(self, data) :
		self._buf += data
		while b'\n' in self._buf :
			line, self._buf = self._buf.split(b'\n', 1)
			line = line.rstrip(b'\r')
			if line :
				self.lineReceived(line)

	def lineReceived(self, line) :
		#dlog("cli result",line)
		line = str(line, "utf-8")

		m = re.match(r'players\s+(\d+)\s+(\d+)\s+(.*)',line)
		if m :
			self.receivedPlayers(m)
			return
		m = re.match(r'artists\s+(\d+)\s+(\d+)\s+(.*)',line)
		if m :
			self.receivedArtists(m)
			return
		m = re.match(r'albums\s+(\d+)\s+(\d+)\s+(.*)',line)
		if m :
			self.receivedAlbums(m)
			return
		m = re.match(r'titles\s+(\d+)\s+(\d+)\s+(.*)',line)
		if m :
			self.receivedTracks(m)
			return
		m = re.match(r'playlists\s+(\d+)\s+(\d+)\s+(.*)',line)
		if m :
			self.receivedPlaylists(m)
			return
		m = re.match(r'playlists\s+tracks\s+(\d+)\s+(\d+)\s+(.*)',line)
		if m :
			self.receivedPlaylistTracks(m)
			return
		m = re.match(r'(\S+) status \S+ \S+ (.*)',line)
		if m :
			self.receivedStatus(m)
			return
		m = re.match(r'(\S+) pause',line)
		if m :
			self.receivedPauseOrPower(m)
			return
		m = re.match(r'(\S+) power',line)
		if m :
			self.receivedPauseOrPower(m)
			return
		m = re.match(r'(\S+) playlist repeat\s+(\d+)\s+(.*)',line)
		if m :
			self.receivedPlaylistRepeat(m)
			return
		m = re.match(r'(\S+) playlist shuffle\s+(\d+)\s+(.*)',line)
		if m :
			self.receivedPlaylistShuffle(m)
			return
		m = re.match(r'(\S+) playlist (.*)',line)
		if m :
			self.receivedPlaylist(m)
			return
		m = re.match(r'\S+ playlistcontrol (.*)',line)
		if m :
			self.receivedPlaylistControl(m)
			return
		m = re.match(r'favorites\s+items\s+(\d+)\s+(\d+)\s+(.*)',line)
		if m :
			self.receivedFavorites(m)
			return
		m = re.match(r'favorites\s+changed',line)
		if m :
			self.receivedFavoritesChanged(m)
			return
		m = re.match(r'pref httpport (\d+)',line)
		if m :
			port = m.group(1)
			app.lms_http_base_url = 'http://' + app.lms_host + ':' + port
			return
		m = re.match(r'rescan\s+(.*)',line)
		if m :
			self.receivedRescan(m)
			return
		m = re.match(r'\S+\s+client\s+.*',line)
		if m :
			self.receivedClient(m)
			return
		dlog("unknown line:",line)


	def addContext(self,future) :
		new_context = str(self.next_context)
		self.next_context += 1
		self.context_map[new_context] = future
		return new_context

	def dispatchResult(self,context,*args) :
		future = self.context_map.pop(context)
		future.set_result(args)

	def receivedPlayers(self,m) :
		(offset,limit,rest) = m.groups()
		offset = int(offset)
		limit = int(limit)
		kvps = rest.split()
		# build up a list of players, each is a dictionary
		players = []
		current_player = None
		for i in kvps :
			#(key,colon,value) = i.partition(':')
			m2 = re.match(r'(\S+?)%3A(.*)',i)
			if not m2 or len(m2.groups()) != 2 :
				elog("unable to parse kvp",i)
				continue
			(key,value) = m2.groups()
			key = unquote(key)
			value = unquote(value)
			#dlog(key,value)
			if key == "count" :
				continue
			elif key == "playerindex" :
				if current_player :
					players.append(current_player)
				current_player = {}
			else :
				current_player[key] = value
		if current_player :
			players.append(current_player)

		control_players = []
		for player in players :
			if not player["isplayer"] :
				continue
			#if player["model"] != "squeezeslave" :
			#	continue
			dlog("found player to control",player["playerid"])
			control_players.append(player["playerid"])

		for player in control_players :
			if player in app.player_source_map :
				self.send(player," status - 1 tags:galduKc subscribe:5")

		app.receivedPlayers(control_players)


	def receivedArtists(self,m) :
		(offset,limit,rest) = m.groups()
		offset = int(offset)
		limit = int(limit)
		kvps = rest.split()
		ids = []
		artists = []
		for i in kvps :
			#(key,colon,value) = i.partition(':')
			m2 = re.match(r'(\S+?)%3A(.*)',i)
			if not m2 or len(m2.groups()) != 2 :
				elog("unable to parse kvp",i)
				continue
			(key,value) = m2.groups()
			key = unquote(key)
			value = unquote(value)
			if key == "count" :
				count = int(value)
			elif key == "id" :
				ids.append(int(value))
			elif key == "artist" :
				artists.append(value)
			elif key == "context" :
				context = value
			elif key == "favorites_url" :
				pass
			else :
				elog("unexpected key",key)

		artist_data = list(zip(ids,artists))
		#dlog("got artists for",offset,limit)
		self.dispatchResult(context,offset,limit,count,artist_data)

	def receivedAlbums(self,m) :
		(offset,limit,rest) = m.groups()
		offset = int(offset)
		limit = int(limit)
		kvps = rest.split()
		ids = []
		albums = []
		artists = []
		sort = None
		for i in kvps :
			#(key,colon,value) = i.partition(':')
			m2 = re.match(r'(\S+?)%3A(.*)',i)
			if not m2 or len(m2.groups()) != 2 :
				elog("unable to parse kvp",i)
				continue
			(key,value) = m2.groups()
			key = unquote(key)
			value = unquote(value)
			#print key,"=",value
			if key == "count" :
				count = int(value)
			elif key == "id" :
				ids.append(int(value))
			elif key == "album" :
				albums.append(value)
			elif key == "artist" :
				artists.append(value)
			elif key == "sort" :
				sort = value
			elif key == "context" :
				context = value
			elif key == "tags" :
				pass
			elif key == "artist_id" :
				dlog("got artist id",value)
				artistid = value
			elif key == "performance" or key == "favorites_url" or key == "favorites_title" :
				pass
			else :
				elog("unexpected key",key)

		dlog("got",len(ids),"albums for",offset,limit)
		# sort is None when getting an artist's albums;
		# sort is "new" when getting newest albums
		if sort == "new" :
			album_data = list(zip(ids,albums,artists))
			#for (albumid,album,artistid) in album_data :
			#	print albumid,album,artistid
			self.dispatchResult(context,album_data)
		else :
			album_data = list(zip(ids,albums))
			app.addCacheArtistAlbums(artistid,offset,limit,count,album_data)
			self.dispatchResult(context,offset,limit,count,album_data)

	def receivedTracks(self,m) :
		(offset,limit,rest) = m.groups()
		offset = int(offset)
		limit = int(limit)
		kvps = rest.split()
		ids = []
		tracks = []
		for i in kvps :
			#(key,colon,value) = i.partition(':')
			m2 = re.match(r'(\S+?)%3A(.*)',i)
			if not m2 or len(m2.groups()) != 2 :
				elog("unable to parse kvp",i)
				continue
			(key,value) = m2.groups()
			key = unquote(key)
			value = unquote(value)
			#print key,"=",value
			if key == "count" :
				count = int(value)
			elif key == "id" :
				ids.append(int(value))
			elif key == "title" :
				tracks.append(value)
			elif key == "album_id" :
				albumid = int(value)
			elif key == "artist" or key == "album" or key == "genre" or key == "duration" or key == "tags" or key == "sort" or key =="tracknum" :
				# useless
				pass
			elif key == "context" :
				context = value
			else :
				elog("unexpected key",key)

		track_data = list(zip(ids,tracks))
		#dlog("got tracks for",offset,limit)
		app.addCacheAlbumTracks(albumid,offset,limit,count,track_data)
		self.dispatchResult(context,offset,limit,count,track_data)

	def receivedPlaylists(self,m) :
		(offset,limit,rest) = m.groups()
		offset = int(offset)
		limit = int(limit)
		kvps = rest.split()
		ids = []
		playlists = []
		for i in kvps :
			#(key,colon,value) = i.partition(':')
			m2 = re.match(r'(\S+?)%3A(.*)',i)
			if not m2 or len(m2.groups()) != 2 :
				elog("unable to parse kvp",i)
				continue
			(key,value) = m2.groups()
			key = unquote(key)
			value = unquote(value)
			#print key,"=",value
			if key == "count" :
				count = int(value)
			elif key == "id" :
				ids.append(int(value))
			elif key == "playlist" :
				playlists.append(value)
			elif key == "context" :
				context = value
			else :
				elog("unexpected key",key)

		playlist_data = list(zip(ids,playlists))
		#dlog("got playlists",offset,limit,playlist_data)
		app.addCachePlaylists(offset,limit,count,playlist_data)
		self.dispatchResult(context,offset,limit,count,playlist_data)

	def receivedPlaylistTracks(self,m) :
		(offset,limit,rest) = m.groups()
		offset = int(offset)
		limit = int(limit)
		kvps = rest.split()
		ids = []
		tracks = []
		for i in kvps :
			#(key,colon,value) = i.partition(':')
			m2 = re.match(r'(\S+?)%3A(.*)',i)
			if not m2 or len(m2.groups()) != 2 :
				elog("unable to parse kvp",i)
				continue
			(key,value) = m2.groups()
			key = unquote(key)
			value = unquote(value)
			#print key,"=",value
			if key == "count" :
				# seems like the squeeze server adds a couple fake ones (for add and delete entries in ui?)
				count = int(value) - 2
			elif key == "id" :
				ids.append(int(value))
			elif key == "title" :
				tracks.append(value)
			elif key == "playlist_id" :
				playlistid = int(value)
			elif key == "artist" or key == "album" or key == "genre" or key == "duration" or key == "tracknum" or key == "tags" or key == "playlist index" or key == "text" or key == "actions" :
				# useless
				pass
			elif key == "context" :
				context = value
			else :
				elog("unexpected key",key)

		track_data = list(zip(ids,tracks))
		#dlog("got tracks for",offset,limit,track_data)
		app.addCachePlaylistTracks(playlistid,offset,limit,count,track_data)
		self.dispatchResult(context,offset,limit,count,track_data)

	def receivedStatus(self,m) :
		(player,rest) = m.groups()
		player = unquote(player)
		kvps = rest.split()
		#print kvps
		data = {}
		for i in kvps :
			#(key,colon,value) = i.partition(':')
			m2 = re.match(r'(\S+?)%3A(.*)',i)
			if not m2 or len(m2.groups()) != 2 :
				elog("unable to parse kvp",i)
				continue
			(key,value) = m2.groups()
			key = unquote(key)
			value = unquote(value)
			#dlog(key,"=",value)
			data[key] = value

		app.receivedStatus(player,data)

	def receivedPlaylistRepeat(self,m) :
		(player,repeat_status,rest) = m.groups()
		player = unquote(player)
		repeat_status = int(repeat_status)
		kvps = rest.split()
		#print kvps
		context = None
		for i in kvps :
			#(key,colon,value) = i.partition(':')
			m2 = re.match(r'(\S+?)%3A(.*)',i)
			if not m2 or len(m2.groups()) != 2 :
				elog("unable to parse kvp",i)
				continue
			(key,value) = m2.groups()
			key = unquote(key)
			value = unquote(value)
			#print key,"=",value
			if key == "context" :
				context = value

		app.receivedRepeatStatus(player,repeat_status)

		if context :
			self.dispatchResult(context)

	def receivedPlaylistShuffle(self,m) :
		(player,shuffle_status,rest) = m.groups()
		player = unquote(player)
		shuffle_status = int(shuffle_status)
		kvps = rest.split()
		#print kvps
		context = None
		for i in kvps :
			#(key,colon,value) = i.partition(':')
			m2 = re.match(r'(\S+?)%3A(.*)',i)
			if not m2 or len(m2.groups()) != 2 :
				elog("unable to parse kvp",i)
				continue
			(key,value) = m2.groups()
			key = unquote(key)
			value = unquote(value)
			#print key,"=",value
			if key == "context" :
				context = value

		app.receivedShuffleStatus(player,shuffle_status)

		if context :
			self.dispatchResult(context)



	def receivedPlaylist(self,m) :
		# certain playlist changes parsed out and handled elsewhere; if we get here,
		# we don't know the specific change and just poll for status
		(player,rest) = m.groups()
		player = unquote(player)
		#print "playlist: ",rest
		self.send(player," status - 1 tags:galduKc")

	def receivedPauseOrPower(self,m) :
		# play state just changed; poll now instead of waiting for the next subscribe:5 tick
		(player,) = m.groups()
		player = unquote(player)
		self.send(player," status - 1 tags:galduKc")

	def receivedPlaylistControl(self,m) :
		(rest,) = m.groups()
		kvps = rest.split()
		#print kvps
		context = None
		for i in kvps :
			#(key,colon,value) = i.partition(':')
			m2 = re.match(r'(\S+?)%3A(.*)',i)
			if not m2 or len(m2.groups()) != 2 :
				elog("unable to parse kvp",i)
				continue
			(key,value) = m2.groups()
			key = unquote(key)
			value = unquote(value)
			#print key,"=",value
			if key == "context" :
				context = value

		if context :
			self.dispatchResult(context)

	def receivedFavorites(self,m) :
		(offset,limit,rest) = m.groups()
		offset = int(offset)
		limit = int(limit)
		kvps = rest.split()
		ids = []
		names = []
		urls = []
		for i in kvps :
			#(key,colon,value) = i.partition(':')
			m2 = re.match(r'(\S+?)%3A(.*)',i)
			if not m2 or len(m2.groups()) != 2 :
				elog("unable to parse kvp",i)
				continue
			(key,value) = m2.groups()
			key = unquote(key)
			value = unquote(value)
			#print key,"=",value
			if key == "count" :
				count = int(value)
			elif key == "id" :
				ids.append(value)
			elif key == "name" :
				names.append(value)
			elif key == "url" :
				urls.append(value)
			elif key == "title" or key == "type" or key == "isaudio" or key == "hasitems" or key == "want_url" :
				pass
			elif key == "context" :
				context = value
			elif key == "image" :
				pass
			else :
				elog("unexpected key",key)

		if len(urls) < len(ids) :
			urls += [''] * (len(ids) - len(urls))
		favorites_data = list(zip(ids,names,urls))
		#dlog("got favorites for",offset,limit,favorites_data)
		self.dispatchResult(context,favorites_data)

	def receivedFavoritesChanged(self,m) :
		app.receivedFavoritesChanged()

	def receivedClient(self,m) :
		self.send("players 0 5")

	def receivedRescan(self,m) :
		(rescan_state,) = m.groups()
		if rescan_state == "done" :
			app.receivedRescanDone()


	def send(self,*args) :
		s = ''.join([str(arg) for arg in args])
		dlog("sending to cli:",s)
		if not self.transport :
			dlog("can't send to LMS when not connected")
			return
		self.transport.write(s.encode('ascii', errors='ignore'))
		self.transport.write(b'\r\n')
