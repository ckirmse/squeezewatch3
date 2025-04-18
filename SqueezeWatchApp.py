#!/usr/bin/python

import sys

from twisted.internet import defer

from Log import *

class SqueezeWatchApp :

	def __init__(self) :
		pass

	def resetAll(self) :
		self.players = []
		self.source_player_map = {}

		self.resetCaches()

	def resetCaches(self) :
		"initializes prefills some caches"

		self.artists = {}
		self.count_artists = None

		self.artist_albums = {}
		self.count_artist_albums = {}

		self.album_tracks = {}
		self.count_album_tracks = {}

		self.playlist_tracks = {}
		self.count_playlist_tracks = {}

		self.favorites = {}
		
		self.newest_albums = {}

		d = defer.Deferred()
		d.addCallback(self.addCacheArtists)
		self.getArtists(d,0,99999)

		d = defer.Deferred()
		d.addCallback(self.addCacheFavorites)
		self.getFavorites(d,0,20)

		d = defer.Deferred()
		d.addCallback(self.addCacheNewestAlbums)
		self.getNewestAlbums(d)

	def getCountArtists(self) :
		return self.count_artists

	def getCountArtistAlbums(self,artistid) :
		return self.count_artist_albums[artistid]

	def getCountAlbumTracks(self,albumid) :
		return self.count_album_tracks[albumid]

	def getCountPlaylists(self) :
		return self.count_playlists

	def getCountPlaylistTracks(self,playlistid) :
		return self.count_playlist_tracks[playlistid]

	def getArtists(self,d,offset,limit) :
		# check cache and return data immediately if we have it
		if offset in self.artists :
			artist_data = []
			for i in range(offset,offset+limit) :
				if i in self.artists :
					artist_data.append(self.artists[i])
			d.callback([offset,limit,self.count_artists,artist_data])
			return

		self.factory.getArtists(d,offset,limit)

	def getArtistAlbums(self,d,artistid,offset,limit) :
		# check cache and return data immediately if we have it
		if artistid in self.artist_albums :
			if offset in self.artist_albums[artistid] :
				album_data = []
				for i in range(offset,offset+limit) :
					if i in self.artist_albums[artistid] :
						album_data.append(self.artist_albums[artistid][i])
				d.callback([offset,limit,self.count_artist_albums[artistid],album_data])
				return
		
		self.factory.getArtistAlbums(d,artistid,offset,limit)

	def getNewestAlbums(self,d) :
		# check cache and return data immediately if we have it
		# note we essentially ignore offset & limit on queries after the first
		if self.newest_albums :
			d.callback([self.newest_albums])
			return

		self.factory.getNewestAlbums(d,0,12)

	def getAlbumTracks(self,d,albumid,offset,limit) :
		# check cache and return data immediately if we have it
		if albumid in self.album_tracks :
			if offset in self.album_tracks[albumid] :
				track_data = []
				for i in range(offset,offset+limit) :
					if i in self.album_tracks[albumid] :
						track_data.append(self.album_tracks[albumid][i])
				d.callback([offset,limit,self.count_album_tracks[albumid],track_data])
				return
		self.factory.getAlbumTracks(d,albumid,offset,limit)

	def getPlaylists(self,d,offset,limit) :
		self.factory.getPlaylists(d,offset,limit)

	def getPlaylistTracks(self,d,playlistid,offset,limit) :
		# check cache and return data immediately if we have it
		if playlistid in self.playlist_tracks :
			if offset in self.playlist_tracks[playlistid] :
				#print "CCC returning playlist tracks from cache"
				track_data = []
				for i in range(offset,offset+limit) :
					if i in self.playlist_tracks[playlistid] :
						track_data.append(self.playlist_tracks[playlistid][i])
				d.callback([offset,limit,self.count_playlist_tracks[playlistid],track_data])
				return
		self.factory.getPlaylistTracks(d,playlistid,offset,limit)

	def getFavorites(self,d,offset,limit) :
		if len(self.favorites) > 0 :
			d.callback(self.favorites)
			return
		self.factory.getFavorites(d,offset,limit)

	def playArtist(self,source,artistid) :
		self.factory.playArtist(self.source_player_map[source],artistid)

	def playAlbum(self,source,albumid,offset=0) :
		self.factory.playAlbum(self.source_player_map[source],albumid,offset)

	def playPlaylist(self,source,playlistid,offset=0) :
		self.factory.playPlaylist(self.source_player_map[source],playlistid,offset)

	def playFavorite(self,source,favoriteid) :
		self.factory.playFavorite(self.source_player_map[source],favoriteid)

	def playPause(self,source) :
		dlog("looking for source",source)
		self.factory.playPause(self.source_player_map[source])

	def pause(self,source) :
		self.factory.pause(self.source_player_map[source])

	def powerOff(self,source) :
		self.factory.powerOff(self.source_player_map[source])

	def getStatus(self,source) :
		for player in self.players :
			self.factory.getStatus(player)

	def prevTrack(self,source) :
		self.factory.prevTrack(self.source_player_map[source])

	def nextTrack(self,source) :
		self.factory.nextTrack(self.source_player_map[source])

	def rewind(self,source) :
		self.factory.rewind(self.source_player_map[source])

	def fastForward(self,source) :
		self.factory.fastForward(self.source_player_map[source])

	def setRepeat(self,d,source,repeat) :
		self.factory.setRepeat(d,self.source_player_map[source],repeat)

	def setShuffle(self,d,source,shuffle) :
		self.factory.setShuffle(d,self.source_player_map[source],shuffle)

	def addCacheArtists(self, tuple_var) :
		offset,limit,count,artist_data = tuple_var
		#dlog("adding cache",count,artist_data)
		index = offset
		for (artistid,artist) in artist_data :
			self.artists[index] = (artistid,artist)
			index += 1
		self.count_artists = count

	def addCacheAlbumTracks(self,albumid,offset,limit,count,track_data) :
		if not albumid in self.album_tracks :
			self.album_tracks[albumid] = {}
		index = offset
		for (trackid,track) in track_data :
			self.album_tracks[albumid][index] = (trackid,track)
			index += 1
		self.count_album_tracks[albumid] = count

	def addCacheArtistAlbums(self,artistid,offset,limit,count,album_data) :
		if not artistid in self.artist_albums :
			self.artist_albums[artistid] = {}
		index = offset
		for (albumid,album) in album_data :
			self.artist_albums[artistid][index] = (albumid,album)
			index += 1
		self.count_artist_albums[artistid] = count

	def addCachePlaylists(self,offset,limit,count,playlist_data) :
		self.count_playlists = count

	def addCachePlaylistTracks(self,playlistid,offset,limit,count,track_data) :
		if not playlistid in self.playlist_tracks :
			self.playlist_tracks[playlistid] = {}
		index = offset
		for (trackid,track) in track_data :
			self.playlist_tracks[playlistid][index] = (trackid,track)
			index += 1
		self.count_playlist_tracks[playlistid] = count

	def addCacheFavorites(self,tuple_var) :
		offset,limit,count,favorites_data = tuple_var
		self.favorites = favorites_data
		app.nuvo_protocol.answerFavorites(favorites_data)

	def addCacheNewestAlbums(self,tuple_var) :
		album_data, = tuple_var
		self.newest_albums = album_data

	def receivedPlayers(self,players) :
		self.players = players
		sources = self.nuvo_protocol.getSources()
		if len(self.players) != len(sources) :
			dlog("got unexpected number of players",len(self.players),"with sources", len(sources))
			dlog(self.players, sources)
			if len(sources) > len(self.players) :
				self.players = self.players[:len(sources)]
			else :
				dlog("fatal more players than sources")
				sys.exit()
		# this is fragile... need to have a static mapping of
		# source 3 -> player 00:00:00:01
		# source 5 -> player whatever
		sources_reverse = list(sources)
		sources_reverse.reverse()
		for (player,source) in zip(self.players,sources_reverse) :
			dlog("source",source,"mapped to player",player)
			self.source_player_map[source] = player

		self.nuvo_protocol.start()

	def receivedArtistAlbums(self,offset,limit,count,album_data) :
		self.nuvo_protocol.answerArtistAlbums(offset,count,album_data)

	def receivedAlbumTracks(self,offset,limit,count,track_data) :
		self.nuvo_protocol.answerAlbumTracks(offset,count,track_data)

	def receivedStatus(self,player,data) :
		if not player in self.players :
			return
		source = self.getSourceForPlayer(player)
		self.nuvo_protocol.answerStatus(source,data)

	def receivedRepeatStatus(self,player,repeat_status) :
		if player != self.players[0] :
			return
		source = self.getSourceForPlayer(player)
		self.nuvo_protocol.answerRepeatStatus(source,repeat_status)

	def receivedShuffleStatus(self,player,shuffle_status) :
		if player != self.players[0] :
			return
		source = self.getSourceForPlayer(player)
		self.nuvo_protocol.answerShuffleStatus(source,shuffle_status)

	def receivedFavoritesChanged(self) :
		self.nuvo_protocol.clearFavorites()
		d = defer.Deferred()
		d.addCallback(self.addCacheFavorites)
		self.getFavorites(d,0,20)

	def receivedRescanDone(self) :
		self.resetCaches()

	def getSourceForPlayer(self,player) :
		source = None
		#dlog("source player map is")
		#for s in self.source_player_map.keys() :
		#	dlog(s," ",self.source_player_map[s])
		for s in self.source_player_map.keys() :
			p = self.source_player_map[s]
			if p == player :
				source = s
		if not source :
			dlog("Unable to find source for player",player)
		return source

app = SqueezeWatchApp()

