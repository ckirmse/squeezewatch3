#!/usr/bin/python

import asyncio

from Log import *

class SqueezeWatchApp :

	def __init__(self) :
		self.lms_host = ''
		self.lms_http_base_url = ''

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

		asyncio.get_event_loop().create_task(self._prefill_caches())

	async def _prefill_caches(self) :
		result = await self.getArtists(0,99999)
		if result :
			self.addCacheArtists(result)
		result = await self.getFavorites(0,20)
		if result :
			self.addCacheFavorites(result)
		result = await self.getNewestAlbums()
		if result :
			self.addCacheNewestAlbums(result)

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

	async def getArtists(self,offset,limit) :
		if offset in self.artists :
			artist_data = []
			for i in range(offset,offset+limit) :
				if i in self.artists :
					artist_data.append(self.artists[i])
			return (offset,limit,self.count_artists,artist_data)
		return await self.factory.getArtists(offset,limit)

	async def getArtistAlbums(self,artistid,offset,limit) :
		if artistid in self.artist_albums :
			if offset in self.artist_albums[artistid] :
				album_data = []
				for i in range(offset,offset+limit) :
					if i in self.artist_albums[artistid] :
						album_data.append(self.artist_albums[artistid][i])
				return (offset,limit,self.count_artist_albums[artistid],album_data)
		return await self.factory.getArtistAlbums(artistid,offset,limit)

	async def getNewestAlbums(self) :
		if self.newest_albums :
			return (self.newest_albums,)
		return await self.factory.getNewestAlbums(0,12)

	async def getAlbumTracks(self,albumid,offset,limit) :
		if albumid in self.album_tracks :
			if offset in self.album_tracks[albumid] :
				track_data = []
				for i in range(offset,offset+limit) :
					if i in self.album_tracks[albumid] :
						track_data.append(self.album_tracks[albumid][i])
				return (offset,limit,self.count_album_tracks[albumid],track_data)
		return await self.factory.getAlbumTracks(albumid,offset,limit)

	async def getPlaylists(self,offset,limit) :
		return await self.factory.getPlaylists(offset,limit)

	async def getPlaylistTracks(self,playlistid,offset,limit) :
		if playlistid in self.playlist_tracks :
			if offset in self.playlist_tracks[playlistid] :
				track_data = []
				for i in range(offset,offset+limit) :
					if i in self.playlist_tracks[playlistid] :
						track_data.append(self.playlist_tracks[playlistid][i])
				return (offset,limit,self.count_playlist_tracks[playlistid],track_data)
		return await self.factory.getPlaylistTracks(playlistid,offset,limit)

	async def getFavorites(self,offset,limit) :
		if self.favorites :
			return self.favorites
		return await self.factory.getFavorites(offset,limit)

	def playArtist(self,source,artistid) :
		if not source in self.source_player_map :
			dlog("no source player map entry for source", source)
			return
		self.factory.playArtist(self.source_player_map[source],artistid)

	def playAlbum(self,source,albumid,offset=0) :
		if not source in self.source_player_map :
			dlog("no source player map entry for source", source)
			return
		self.factory.playAlbum(self.source_player_map[source],albumid,offset)

	def playPlaylist(self,source,playlistid,offset=0) :
		if not source in self.source_player_map :
			dlog("no source player map entry for source", source)
			return
		self.factory.playPlaylist(self.source_player_map[source],playlistid,offset)

	def playFavorite(self,source,favoriteid) :
		if not source in self.source_player_map :
			dlog("no source player map entry for source", source)
			return
		self.factory.playFavorite(self.source_player_map[source],favoriteid)

	def playPause(self,source) :
		if not source in self.source_player_map :
			dlog("no source player map entry for source", source)
			return
		self.factory.playPause(self.source_player_map[source])

	def pause(self,source) :
		if not source in self.source_player_map :
			dlog("no source player map entry for source", source)
			return
		self.factory.pause(self.source_player_map[source])

	def powerOff(self,source) :
		if not source in self.source_player_map :
			dlog("no source player map entry for source", source)
			return
		self.factory.powerOff(self.source_player_map[source])

	def getStatus(self,source) :
		for player in self.players :
			self.factory.getStatus(player)

	def prevTrack(self,source) :
		if not source in self.source_player_map :
			dlog("no source player map entry for source", source)
			return
		if self._playAdjacentFavorite(source, -1) :
			return
		self.factory.prevTrack(self.source_player_map[source])

	def nextTrack(self,source) :
		if not source in self.source_player_map :
			dlog("no source player map entry for source", source)
			return
		if self._playAdjacentFavorite(source, 1) :
			return
		self.factory.nextTrack(self.source_player_map[source])

	def _playAdjacentFavorite(self,source,direction) :
		info = self.nuvo_protocol.getSourceStreamInfo(source)
		if info is None :
			return False
		(is_stream, url, mode) = info
		if not is_stream or not url or not self.favorites :
			return False
		favorites_list, = self.favorites
		urls = [fav_url for (_, _, fav_url) in favorites_list]
		if url not in urls :
			return False
		index = urls.index(url)
		new_index = (index + direction) % len(favorites_list)
		favorite_id = favorites_list[new_index][0]
		self.factory.playFavorite(self.source_player_map[source], favorite_id)
		return True

	def rewind(self,source) :
		if not source in self.source_player_map :
			dlog("no source player map entry for source", source)
			return
		self.factory.rewind(self.source_player_map[source])

	def fastForward(self,source) :
		if not source in self.source_player_map :
			dlog("no source player map entry for source", source)
			return
		self.factory.fastForward(self.source_player_map[source])

	async def setRepeat(self,source,repeat) :
		if not source in self.source_player_map :
			dlog("no source player map entry for source", source)
			return
		await self.factory.setRepeat(self.source_player_map[source],repeat)

	async def setShuffle(self,source,shuffle) :
		if not source in self.source_player_map :
			dlog("no source player map entry for source", source)
			return
		await self.factory.setShuffle(self.source_player_map[source],shuffle)

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

	def addCacheFavorites(self,favorites_data) :
		self.favorites = favorites_data

	def addCacheNewestAlbums(self,tuple_var) :
		album_data, = tuple_var
		self.newest_albums = album_data

	def playStreamIfNeeded(self,source) :
		if source not in self.source_player_map :
			return
		info = self.nuvo_protocol.getSourceStreamInfo(source)
		if info is None :
			return
		(is_stream, url, mode) = info
		if is_stream and url and mode != 'play' :
			self.factory.playUrl(self.source_player_map[source], url)

	def playPauseOrStream(self,source) :
		info = self.nuvo_protocol.getSourceStreamInfo(source)
		if info is not None :
			(is_stream, url, mode) = info
			if is_stream and url and mode != 'play' :
				self.factory.playUrl(self.source_player_map[source], url)
				return
		self.playPause(source)

	def receivedPlayers(self,players) :
		self.players = players
		for player in players :
			if player in self.player_source_map :
				source = self.player_source_map[player]
				dlog("source",source,"mapped to player",player)
				self.source_player_map[source] = player
			else :
				dlog("unknown player, no source mapping:",player)

		self.nuvo_protocol.start()

	def receivedArtistAlbums(self,offset,limit,count,album_data) :
		self.nuvo_protocol.answerArtistAlbums(offset,count,album_data)

	def receivedAlbumTracks(self,offset,limit,count,track_data) :
		self.nuvo_protocol.answerAlbumTracks(offset,count,track_data)

	def receivedStatus(self,player,data) :
		if not player in self.players :
			return
		source = self.getSourceForPlayer(player)
		if source is None :
			return
		self.nuvo_protocol.answerStatus(source,data)

	def receivedRepeatStatus(self,player,repeat_status) :
		if player != self.players[0] :
			return
		source = self.getSourceForPlayer(player)
		if source is None :
			return
		self.nuvo_protocol.answerRepeatStatus(source,repeat_status)

	def receivedShuffleStatus(self,player,shuffle_status) :
		if player != self.players[0] :
			return
		source = self.getSourceForPlayer(player)
		if source is None :
			return
		self.nuvo_protocol.answerShuffleStatus(source,shuffle_status)

	def receivedFavoritesChanged(self) :
		self.nuvo_protocol.clearFavorites()
		self.favorites = {}
		asyncio.get_event_loop().create_task(self._refresh_favorites())

	async def _refresh_favorites(self) :
		result = await self.getFavorites(0,20)
		if result :
			self.addCacheFavorites(result)
			app.nuvo_protocol.answerFavorites(result)

	def receivedRescanDone(self) :
		self.resetCaches()

	def getSourceForPlayer(self,player) :
		source = None
		for s in self.source_player_map.keys() :
			p = self.source_player_map[s]
			if p == player :
				source = s
		if not source :
			dlog("Unable to find source for player",player)
		return source

app = SqueezeWatchApp()
