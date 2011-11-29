#!/usr/bin/python

import time

from twisted.internet import defer
from twisted.internet import reactor

from Log import *

from SqueezeWatchApp import app

class NuVoZone :

	states = {
		1 : 'StateMain',
		2 : 'StateArtists',
		3 : 'StateArtistAlbums',
		4 : 'StateArtistAlbumTracks',
		5 : 'StatePlaylists',
		6 : 'StatePlaylistTracks',
		7 : 'StateNewestAlbums',
		8 : 'StateSettings',
		}

	# presses less than this long go to prev/next track
	press_track_time = 0.5
	# each (this time) held down, skip within song
	press_skip_initial_delay = 0.5
	press_skip_subsequent_delay = 3.0

	# how long to let a zone under a source we control be idle
	idle_time = 300.0
	# how long to let a zone be on for a source we don't control
	uncontrolled_source_time = 10800.0

	def __init__(self,nuvo,zone,name) :
		self.nuvo = nuvo
		self.zone = zone
		self.name = name

		self.source = 0
		self.idle_timer = None

		self.menuid_artists = 27
		self.menuid_artist_albums = 28
		self.menuid_artist_album_tracks = 29
		self.menuid_playlists = 30
		self.menuid_playlist_tracks = 31
		self.menuid_newest_albums = 32
		self.menuid_settings = 33

		# make class state constants first time
		if not hasattr(NuVoZone,'StateMain') :
			for num, state_name in self.states.iteritems() :
				setattr(NuVoZone,state_name,num)
		self.state = self.StateMain
		self.menu_item_index = None
		# StateArtistsMain variables
		self.prev_down = None
		self.prev_delayed_call = None
		self.next_down = None
		self.next_delayed_call = None
		# StateArtists variables
		self.artist_menu_map = {}
		self.artist_menu_last_chosen_index = 0
		# StateArtistAlbums variables
		self.menu_artist_itemid = None
		self.menu_artist_name = None
		self.menu_artistid = None
		self.artist_albums_menu_map = {}
		# StateArtistAlbumTracks
		self.menu_artist_album_itemid = None
		self.menu_artist_album_name = None
		self.menu_artist_albumid = None
		self.artist_album_tracks_menu_map = {}
		# StatePlaylists
		self.playlist_menu_map = {}
		# StatePlaylistTracks
		self.menu_playlist_itemid = None
		self.menu_playlist_name = None
		self.playlist_tracks_menu_map = {}
		# StateNewestAlbums
		self.newest_albums_menu_map = {}
		# StateSettings

	def getZoneID(self) :
		return self.zone

	def isOn(self) :
		return self.source != 0

	def getSource(self) :
		return self.source

	def setState(self,new_state) :
		if self.state == new_state :
			elog("attempt to set state to itself",self.state)
			return

		self.resetIdleTimer()

		prev_state = self.state

		if prev_state == self.StateMain :
			self.prev_down = None
			if self.prev_delayed_call :
				self.prev_delayed_call.cancel()
				self.prev_delayed_call = None
			self.next_down = None
			if self.next_delayed_call :
				self.next_delayed_call.cancel()
				self.next_delayed_call = None

		self.state = new_state

		if self.state == self.StateMain :
			self.dispinfo = None
			self.displines = None
		elif self.state == self.StateArtists :
			d = defer.Deferred()
			d.addCallback(self.answerArtists,first_in_state=True)
			app.getArtists(d,0,20)
		elif self.state == self.StateArtistAlbums :
			d = defer.Deferred()
			d.addCallback(self.answerArtistAlbums)
			#print "sending for artist albums",self.menu_artistid
			app.getArtistAlbums(d,self.menu_artistid,0,20)
		elif self.state == self.StateArtistAlbumTracks :
			d = defer.Deferred()
			d.addCallback(self.answerAlbumTracks)
			app.getAlbumTracks(d,self.menu_artist_albumid,0,20)
		elif self.state == self.StatePlaylists :
			d = defer.Deferred()
			d.addCallback(self.answerPlaylists)
			app.getPlaylists(d,0,20)
		elif self.state == self.StatePlaylistTracks :
			d = defer.Deferred()
			d.addCallback(self.answerPlaylistTracks)
			app.getPlaylistTracks(d,self.menu_playlistid,0,20)
		elif self.state == self.StateNewestAlbums :
			d = defer.Deferred()
			d.addCallback(self.answerNewestAlbums)
			app.getNewestAlbums(d)
		elif self.state == self.StateSettings :
			self.sendSettingsMenu()

	def answerArtists(self,(offset,limit,count,artist_data),first_in_state=False) :
		#dlog("have",len(artist_data),"artists")
		current_index = '0xFFFF'
		if self.menu_item_index :
			current_index = self.menu_item_index-1
		if first_in_state :
			#print "YYY using",self.artist_menu_last_chosen_index
			current_index = self.artist_menu_last_chosen_index
		self.menu_item_index = None # don't set our position next time
		#current_index = self.artist_menu_index
		self.nuvo.sendMenu(self.source,self.zone,self.menuid_artists,count,current_index,offset,len(artist_data),"Artists")
		index = offset
		for (artistid,artist) in artist_data :
			index += 1
			self.artist_menu_map[index] = (artistid,artist)
			self.nuvo.sendMenuItem(self.source,self.zone,index,3,artist)

	def answerArtistAlbums(self,(offset,limit,count,album_data)) :
		#dlog("have",len(album_data),"albums")
		current_index = '0xFFFF'
		if self.menu_item_index :
			current_index = self.menu_item_index-1
		self.menu_item_index = None # don't set our position next time
		self.nuvo.sendMenu(self.source,self.zone,self.menuid_artist_albums,count,current_index,offset,len(album_data),self.menu_artist_name)
		index = 0
		for (albumid,album) in album_data :
			index += 1
			self.artist_albums_menu_map[index] = (albumid,album)
			self.nuvo.sendMenuItem(self.source,self.zone,index,3,album)
		
	def answerAlbumTracks(self,(offset,limit,count,track_data)) :
		#dlog("have",len(track_data),"tracks")
		self.nuvo.sendMenu(self.source,self.zone,self.menuid_artist_album_tracks,count,'0xFFFF',offset,len(track_data),self.menu_artist_album_name)
		index = offset
		for (trackid,track) in track_data :
			index += 1
			self.artist_album_tracks_menu_map[index] = (trackid,track)
			self.nuvo.sendMenuItem(self.source,self.zone,index,2,str(index) + ". " + track)
		
	def answerPlaylists(self,(offset,limit,count,playlist_data)) :
		#dlog("have",len(playlist_data),"playlists")
		current_index = '0xFFFF'
		if self.menu_item_index :
			current_index = self.menu_item_index-1
		self.menu_item_index = None # don't set our position next time
		self.nuvo.sendMenu(self.source,self.zone,self.menuid_playlists,count,current_index,offset,len(playlist_data),"Playlists")
		index = offset
		for (playlistid,playlist) in playlist_data :
			index += 1
			self.playlist_menu_map[index] = (playlistid,playlist)
			self.nuvo.sendMenuItem(self.source,self.zone,index,3,playlist)

	def answerSettingsChanged(self,junk) :
		# if still in settings mode, redisplay menu
		if self.state == self.StateSettings :
			self.sendSettingsMenu()

	def answerPlaylistTracks(self,(offset,limit,count,track_data)) :
		#dlog("have",len(track_data),"tracks")
		self.nuvo.sendMenu(self.source,self.zone,self.menuid_playlist_tracks,count,'0xFFFF',offset,len(track_data),self.menu_playlist_name)
		index = offset
		for (trackid,track) in track_data :
			index += 1
			self.playlist_tracks_menu_map[index] = (trackid,track)
			self.nuvo.sendMenuItem(self.source,self.zone,index,2,str(index) + ". " + track)

	def answerNewestAlbums(self,(album_data,)) :
		#dlog("have",len(album_data),"newest albums")
		current_index = '0xFFFF'
		if self.menu_item_index :
			current_index = self.menu_item_index-1
		self.menu_item_index = None # don't set our position next time
		self.nuvo.sendMenu(self.source,self.zone,self.menuid_newest_albums,len(album_data),current_index,0,len(album_data),"New Music")
		index = 0
		for (albumid,album,artist) in album_data :
			index += 1
			self.newest_albums_menu_map[index] = (albumid,album)
			self.nuvo.sendMenuItem(self.source,self.zone,index,2,artist + " - " + album)

	def sendSettingsMenu(self) :
		repeat = self.nuvo.getRepeatStatus(self.source)
		shuffle = self.nuvo.getShuffleStatus(self.source)

		self.nuvo.sendMenu(self.source,self.zone,self.menuid_settings,2,'0xFFFF',0,2,'Settings')
		repeat_str = 'Repeat '
		if repeat == 0 :
			repeat_str += 'Off'
		elif repeat == 1 :
			repeat_str += 'Song'
		elif repeat == 2 :
			repeat_str += 'Playlist'
		else :
			repeat_str += 'Unknown ' + str(repeat)
		shuffle_str = 'Shuffle '
		if shuffle == 0 :
			shuffle_str += 'Off'
		elif shuffle == 1 :
			shuffle_str += 'Song'
		elif shuffle == 2 :
			shuffle_str += 'Playlist'
		else :
			shuffle_str += 'Unknown ' + str(shuffle)
		self.nuvo.sendMenuItem(self.source,self.zone,1,2,repeat_str)
		self.nuvo.sendMenuItem(self.source,self.zone,2,2,shuffle_str)

	def receivedButton(self,source,button,action,menuid,itemid,itemindex) :
		source = int(source)
		if self.source == 0 :
			self.source = source

		if self.state == self.StateMain :
			if button == 2 :
				# play/pause
				if action == 2 :
					# button up
					app.playPause(self.source)
				return
			elif button == 3 :
				# prev
				if action == 1 :
					self.prev_down = time.time()
					self.prev_delayed_call = reactor.callLater(self.press_skip_initial_delay,self.holdingPrev)
				if action == 2 :
					if self.prev_delayed_call :
						self.prev_delayed_call.cancel()
						self.prev_delayed_call = None
					pressed_time = time.time() - self.prev_down
					if pressed_time < self.press_track_time :
						app.prevTrack(self.source)
			elif button == 4 :
				# next
				if action == 1 :
					self.next_down = time.time()
					self.next_delayed_call = reactor.callLater(self.press_skip_initial_delay,self.holdingNext)
				if action == 2 :
					if self.next_delayed_call :
						self.next_delayed_call.cancel()
						self.next_delayed_call = None
					pressed_time = time.time() - self.next_down
					if pressed_time < self.press_track_time :
						app.nextTrack(self.source)

		# ignore button down; just look for button up in menus
		if action != 2 :
			return

		if menuid == 0xFFFFFFFF :
			#print "got top level menu selection"
			#these need to match up the data sent in NuVoProtocol
			if itemid == 1 :
				#print "artists menu"
				self.menu_item_index = 0
				self.setState(self.StateArtists)
				return
			elif itemid == 2 :
				#print "playlists menu"
				self.menu_item_index = 0
				self.setState(self.StatePlaylists)
				return
			elif itemid == 3 :
				#print "newest albums menu"
				self.menu_item_index = 0
				self.setState(self.StateNewestAlbums)
				return
			elif itemid == 4 :
				#print "settings menu"
				self.menu_item_index = 0
				self.setState(self.StateSettings)
				return

		if menuid == self.menuid_artists :
			if button == 1 :
				# OK
				#dlog("show menu for artist itemid",itemid)
				#for index,(artistid,artist) in self.artist_menu_map.iteritems() :
				#	print "menuid",index,"artistid",artistid,artist
				self.artist_menu_last_chosen_index = itemindex
				self.menu_artist_itemid = itemid
				(self.menu_artistid,self.menu_artist_name) = self.artist_menu_map[itemid]
				self.setState(self.StateArtistAlbums)
			elif button == 2 :
				# play
				(artistid,album) = self.artist_menu_map[itemid]
				app.playArtist(self.source,artistid)
				self.nuvo.sendExitMenu(self.source,self.zone)
				self.setState(self.StateMain)
			return

		if menuid == self.menuid_artist_albums :
			if button == 1 :
				# OK
				#dlog("show tracks for this album")
				self.menu_artist_album_itemid = itemid
				(self.menu_artist_albumid,self.menu_artist_album_name) = self.artist_albums_menu_map[itemid]
				self.setState(self.StateArtistAlbumTracks)
			elif button == 2 :
				# play
				(albumid,album) = self.artist_albums_menu_map[itemid]
				app.playAlbum(self.source,albumid)
				self.nuvo.sendExitMenu(self.source,self.zone)
				self.setState(self.StateMain)
			return

		if menuid == self.menuid_artist_album_tracks :
			if button == 1 :
				# OK
				dlog("should show data for this track")
			elif button == 2 :
				# play
				# load up all album, but start at this track in it
				app.playAlbum(self.source,self.menu_artist_albumid,itemindex)
				self.nuvo.sendExitMenu(self.source,self.zone)
				self.setState(self.StateMain)
			return
				
		if menuid == self.menuid_playlists :
			if button == 1 :
				# OK
				#dlog("show menu for playlist itemid",itemid)
				self.menu_playlist_itemid = itemid
				(self.menu_playlistid,self.menu_playlist_name) = self.playlist_menu_map[itemid]
				self.setState(self.StatePlaylistTracks)
			elif button == 2 :
				# play
				(playlistid,playlist) = self.playlist_menu_map[itemid]
				app.playPlaylist(self.source,playlistid)
				self.nuvo.sendExitMenu(self.source,self.zone)
				self.setState(self.StateMain)
			return

		if menuid == self.menuid_playlist_tracks :
			if button == 1 :
				# OK
				dlog("should show data for this track")
			elif button == 2 :
				# play
				# load up all playlist, but start at this track in it
				app.playPlaylist(self.source,self.menu_playlistid,itemindex)
				self.nuvo.sendExitMenu(self.source,self.zone)
				self.setState(self.StateMain)
			return

		if menuid == self.menuid_newest_albums :
			if button == 1 or button == 2:
				# OK or play
				(albumid,album) = self.newest_albums_menu_map[itemid]
				app.playAlbum(self.source,albumid)
				self.nuvo.sendExitMenu(self.source,self.zone)
				self.setState(self.StateMain)
			return
			
		if menuid == self.menuid_settings :
			if button == 1 :
				# OK
				d = defer.Deferred()
				d.addCallback(self.answerSettingsChanged)
				if itemindex == 0 :
					app.setRepeat(d,self.source,self.nuvo.getNextRepeatStatus(self.source))
				elif itemindex == 1 :
					app.setShuffle(d,self.source,self.nuvo.getNextShuffleStatus(self.source))
				else :
					elog("Unknown settings item",itemindex)
			elif button == 2 :
				pass
			return

	def receivedMenuRequest(self,source,menuid,up,location,itemindex) :
		source = int(source)
		if self.source == 0 :
			self.source = source

		if up :
			if self.state == self.StateArtists :
				# go back to main menu
				self.setState(self.StateMain)
				self.nuvo.sendMainMenu(self.source,self.zone)
			elif self.state == self.StateArtistAlbums :
				# go back to artists menu, preferably with this artist selected
				self.menu_item_index = self.menu_artist_itemid
				self.setState(self.StateArtists)
			elif self.state == self.StateArtistAlbumTracks :
				# go back to artist albums menu, preferably with this album selected
				self.menu_item_index = self.menu_artist_album_itemid
				self.setState(self.StateArtistAlbums)
			elif self.state == self.StatePlaylists :
				# go back to main menu
				self.setState(self.StateMain)
				self.nuvo.sendMainMenu(self.source,self.zone)
			elif self.state == self.StatePlaylistTracks :
				# go back to playlists menu, preferably with this playlist selected
				self.menu_item_index = self.menu_playlist_itemid
				self.setState(self.StatePlaylists)
			elif self.state == self.StateNewestAlbums :
				# go back to main menu
				self.setState(self.StateMain)
				self.nuvo.sendMainMenu(self.source,self.zone)
			elif self.state == self.StateSettings :
				# go back to main menu
				self.setState(self.StateMain)
				self.nuvo.sendMainMenu(self.source,self.zone)
			else :
				elog("receivedmenuRequest unknown state ",self.state)
			return
		
		if menuid == self.menuid_artists :
			if location == 0 :
				# home button
				start = 0
			elif location == 1 :
				# end button
				start = max(0,app.getCountArtists()-19)
			elif location == 2 :
				# start with itemindex
				start = itemindex
			elif location == 3 :
				# end with itemindex
				start = max(0,itemindex-19)
			d = defer.Deferred()
			d.addCallback(self.answerArtists)
			app.getArtists(d,start,20)
			return

		elif menuid == self.menuid_artist_albums :
			if location == 0 :
				# home button
				start = 0
			elif location == 1 :
				# end button
				start = max(0,app.getCountArtistAlbums(self.menu_artistid)-19)
			elif location == 2 :
				# start with itemindex
				start = itemindex
			elif location == 3 :
				# end with itemindex
				start = max(0,itemindex-19)
			d = defer.Deferred()
			d.addCallback(self.answerArtistAlbums)
			app.getArtistAlbums(d,self.menu_artistid,start,20)
			return

		elif menuid == self.menuid_artist_album_tracks :
			if location == 0 :
				# home button
				start = 0
			elif location == 1 :
				# end button
				start = max(0,app.getCountAlbumTracks(self.menu_artist_albumid)-19)
			elif location == 2 :
				# start with itemindex
				start = itemindex
			elif location == 3 :
				# end with itemindex
				start = max(0,itemindex-19)
			d = defer.Deferred()
			d.addCallback(self.answerAlbumTracks)
			app.getAlbumTracks(d,self.menu_artist_albumid,start,20)
			return

		if menuid == self.menuid_playlists :
			if location == 0 :
				# home button
				start = 0
			elif location == 1 :
				# end button
				start = max(0,app.getCountPlaylists()-19)
			elif location == 2 :
				# start with itemindex
				start = itemindex
			elif location == 3 :
				# end with itemindex
				start = max(0,itemindex-19)
			d = defer.Deferred()
			d.addCallback(self.answerArtists)
			app.getArtists(d,start,20)
			return

		if menuid == self.menuid_playlist_tracks :
			if location == 0 :
				# home button
				start = 0
			elif location == 1 :
				# end button
				start = max(0,app.getCountPlaylistTracks(self.menu_playlistid)-19)
			elif location == 2 :
				# start with itemindex
				start = itemindex
			elif location == 3 :
				# end with itemindex
				start = max(0,itemindex-19)
			d = defer.Deferred()
			d.addCallback(self.answerPlaylistTracks)
			app.getPlaylistTracks(d,self.menu_playlistid,start,20)
			return

		elog('unknown menu',menuid)
		
	def receivedMenuActive(self,exit) :
		if exit :
			self.setState(self.StateMain)

	def receivedOff(self) :
		self.source = 0
		if self.idle_timer != None :
			self.idle_timer.cancel()
			self.idle_timer = nil
	
	def receivedOnSource(self,source) :
		self.source = source
		self.resetIdleTimer()

	def resetIdleTimer(self) :
		if self.source in app.nuvo_protocol.getSources() :
			# it's a source we control--we should auto-time out as normal
			#dlog("going to a local source for zone",self.zone)
			if self.idle_timer :
				#dlog("resetting short timer")
				self.idle_timer.reset(self.idle_time)
			else :
				#dlog("initiating short timer")
				self.idle_timer = reactor.callLater(self.idle_time,self.notifyIdleTimer)
		else :
			# it's some other source; long auto timer
			#dlog("going to an uncontrolled source for zone",self.zone)
			if self.idle_timer :
				#dlog("resetting long timer")
				self.idle_timer.reset(self.uncontrolled_source_time)
			else :
				#dlog("initiating long timer")
				self.idle_timer = reactor.callLater(self.uncontrolled_source_time,self.notifyIdleTimer)

	def notifyStatusChanged(self) :
		if self.idle_timer != None :
			#dlog("zone",self.zone,"status changed")
			self.idle_timer.reset(self.idle_time)
		
	def notifyIdleTimer(self) :
		dlog("idle timeout for zone",self.zone)
		self.idle_timer = None
		app.nuvo_protocol.sendZoneOff(self.zone)

	def holdingPrev(self) :
		app.rewind(self.source)
		self.prev_delayed_call = reactor.callLater(self.press_skip_subsequent_delay,self.holdingPrev)


	def holdingNext(self) :
		app.fastForward(self.source)
		self.next_delayed_call = reactor.callLater(self.press_skip_subsequent_delay,self.holdingNext)

