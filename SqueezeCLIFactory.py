#!/usr/bin/python

from twisted.internet import defer
from twisted.internet.protocol import ReconnectingClientFactory
from twisted.internet import reactor

from zigutils import *
from Log import *

from SqueezeWatchApp import app

class SqueezeCLIFactory(ReconnectingClientFactory) :

	def __init__(self) :
		self.connector = None

	def getArtists(self,d,offset,limit) :
		if not self.connector :
			return
		
		context = self.connector.addContext(d)
		self.connector.send("artists ",offset," ",limit," context:",context)

	def getArtistAlbums(self,d,artistid,offset,limit) :
		if not self.connector :
			return

		context = self.connector.addContext(d)
		self.connector.send("albums ",offset," ",limit," artist_id:",artistid," context:",context)

	def getNewestAlbums(self,d,offset,limit) :
		if not self.connector :
			return

		context = self.connector.addContext(d)
		self.connector.send("albums ",offset," ",limit," sort:new"," tags:la"," context:",context)

	def getAlbumTracks(self,d,albumid,offset,limit) :
		if not self.connector :
			return
		context = self.connector.addContext(d)
		self.connector.send("titles ",offset," ",limit," tags:t sort:tracknum album_id:",albumid," context:",context)

	def getPlaylists(self,d,offset,limit) :
		if not self.connector :
			return
		
		context = self.connector.addContext(d)
		self.connector.send("playlists ",offset," ",limit," context:",context)

	def getPlaylistTracks(self,d,playlistid,offset,limit) :
		if not self.connector :
			return
		context = self.connector.addContext(d)
		self.connector.send("playlists tracks ",offset," ",limit," tags:t playlist_id:",playlistid," context:",context)

	def getFavorites(self,d,offset,limit) :
		if not self.connector :
			return
		context = self.connector.addContext(d)
		self.connector.send("favorites items ",offset," ",limit," context:",context)

	def playArtist(self,player,artistid) :
		if not self.connector :
			return
		self.connector.send(player," playlistcontrol cmd:load artist_id:",artistid)

	def playAlbum(self,player,albumid,offset) :
		if not self.connector :
			return
		context_str = ""
		if offset :
			d = defer.Deferred()
			d.addCallback(self.setPlaylistOffset,player,offset)
			context = self.connector.addContext(d)
			context_str = " context:" + context
		self.connector.send(player," playlistcontrol cmd:load album_id:",albumid,context_str)

	def playPlaylist(self,player,playlistid,offset) :
		if not self.connector :
			return

		context_str = ""
		if offset :
			d = defer.Deferred()
			d.addCallback(self.setPlaylistOffset,player,offset)
			context = self.connector.addContext(d)
			context_str = " context:" + context
		self.connector.send(player," playlistcontrol cmd:load playlist_id:",playlistid,context_str)

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

	def setRepeat(self,d,player,repeat) :
		if not self.connector :
			return
		
		context = self.connector.addContext(d)
		self.connector.send(player," playlist repeat ",repeat," context:",context)

	def setShuffle(self,d,player,shuffle) :
		if not self.connector :
			return
		
		context = self.connector.addContext(d)
		self.connector.send(player," playlist shuffle ",shuffle," context:",context)

	### callbacks from our deferreds to chain requests

	def setPlaylistOffset(self,player,empty,offset) :
		"Called by a deferred from playAlbum or playPlaylist to start within a list"
		self.connector.send(player," playlist index +",offset)

	### callbacks from our protocol

	def notifyConnectionMade(self,connector) :
		log("Connected to",connector)
		self.connector = connector
		app.resetAll()

	### callbacks from ClientFactory

	def startedConnecting(self,connector) :
		log("Connecting to ",connector)

	def clientConnectionFailed(self,connector,reason) :
		dlog("Connect attempt failed:",reason.getErrorMessage())
		ReconnectingClientFactory.clientConnectionFailed(self,connector,reason)

	def clientConnectionLost(self,connector,reason) :
		log("Disconnected:",reason.getErrorMessage())
		self.connector = None
		ReconnectingClientFactory.clientConnectionLost(self,connector,reason)



