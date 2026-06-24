#!/usr/bin/python

import asyncio

from zigutils import *
from Log import *

from SqueezeWatchApp import app

class SqueezeCLIFactory :

	def __init__(self) :
		self.connector = None

	async def getArtists(self,offset,limit) :
		if not self.connector :
			return None
		future = asyncio.get_event_loop().create_future()
		context = self.connector.addContext(future)
		self.connector.send("artists ",offset," ",limit," context:",context)
		return await future

	async def getArtistAlbums(self,artistid,offset,limit) :
		if not self.connector :
			return None
		future = asyncio.get_event_loop().create_future()
		context = self.connector.addContext(future)
		self.connector.send("albums ",offset," ",limit," artist_id:",artistid," context:",context)
		return await future

	async def getNewestAlbums(self,offset,limit) :
		if not self.connector :
			return None
		future = asyncio.get_event_loop().create_future()
		context = self.connector.addContext(future)
		self.connector.send("albums ",offset," ",limit," sort:new"," tags:la"," context:",context)
		return await future

	async def getAlbumTracks(self,albumid,offset,limit) :
		if not self.connector :
			return None
		future = asyncio.get_event_loop().create_future()
		context = self.connector.addContext(future)
		self.connector.send("titles ",offset," ",limit," tags:t sort:tracknum album_id:",albumid," context:",context)
		return await future

	async def getPlaylists(self,offset,limit) :
		if not self.connector :
			return None
		future = asyncio.get_event_loop().create_future()
		context = self.connector.addContext(future)
		self.connector.send("playlists ",offset," ",limit," context:",context)
		return await future

	async def getPlaylistTracks(self,playlistid,offset,limit) :
		if not self.connector :
			return None
		future = asyncio.get_event_loop().create_future()
		context = self.connector.addContext(future)
		self.connector.send("playlists tracks ",offset," ",limit," tags:t playlist_id:",playlistid," context:",context)
		return await future

	async def getFavorites(self,offset,limit) :
		if not self.connector :
			return None
		future = asyncio.get_event_loop().create_future()
		context = self.connector.addContext(future)
		self.connector.send("favorites items ",offset," ",limit," context:",context)
		return await future

	def playArtist(self,player,artistid) :
		if not self.connector :
			return
		self.connector.send(player," playlistcontrol cmd:load artist_id:",artistid)

	def playAlbum(self,player,albumid,offset) :
		if not self.connector :
			return
		if offset :
			asyncio.get_event_loop().create_task(self._playAlbumWithOffset(player,albumid,offset))
		else :
			self.connector.send(player," playlistcontrol cmd:load album_id:",albumid)

	async def _playAlbumWithOffset(self,player,albumid,offset) :
		future = asyncio.get_event_loop().create_future()
		context = self.connector.addContext(future)
		self.connector.send(player," playlistcontrol cmd:load album_id:",albumid," context:",context)
		await future
		self.connector.send(player," playlist index +",offset)

	def playPlaylist(self,player,playlistid,offset) :
		if not self.connector :
			return
		if offset :
			asyncio.get_event_loop().create_task(self._playPlaylistWithOffset(player,playlistid,offset))
		else :
			self.connector.send(player," playlistcontrol cmd:load playlist_id:",playlistid)

	async def _playPlaylistWithOffset(self,player,playlistid,offset) :
		future = asyncio.get_event_loop().create_future()
		context = self.connector.addContext(future)
		self.connector.send(player," playlistcontrol cmd:load playlist_id:",playlistid," context:",context)
		await future
		self.connector.send(player," playlist index +",offset)

	def playUrl(self,player,url) :
		if not self.connector :
			return
		self.connector.send(player," playlist play ",url)

	def playFavorite(self,player,favoriteid) :
		if not self.connector :
			return

		self.connector.send(player," favorites playlist play item_id:",favoriteid)

	def playPause(self,player) :
		if not self.connector :
			return

		self.connector.send(player," pause")

	def pause(self,player) :
		if not self.connector :
			return

		self.connector.send(player," pause 1")

	def powerOff(self,player) :
		if not self.connector :
			return

		self.connector.send(player," power 0")

	def getStatus(self,player) :
		if not self.connector :
			return

		self.connector.send(player," status - 1")

	def prevTrack(self,player) :
		if not self.connector :
			return

		self.connector.send(player," button rew.single")

	def nextTrack(self,player) :
		if not self.connector :
			return

		self.connector.send(player," button fwd.single")

	def rewind(self,player) :
		if not self.connector :
			return

		self.connector.send(player," time -10")

	def fastForward(self,player) :
		if not self.connector :
			return

		self.connector.send(player," time +30")

	async def setRepeat(self,player,repeat) :
		if not self.connector :
			return
		future = asyncio.get_event_loop().create_future()
		context = self.connector.addContext(future)
		self.connector.send(player," playlist repeat ",repeat," context:",context)
		await future

	async def setShuffle(self,player,shuffle) :
		if not self.connector :
			return
		future = asyncio.get_event_loop().create_future()
		context = self.connector.addContext(future)
		self.connector.send(player," playlist shuffle ",shuffle," context:",context)
		await future

	### callbacks from our protocol

	def notifyConnectionMade(self,connector) :
		log("Connected to",connector)
		self.connector = connector
		app.resetAll()
