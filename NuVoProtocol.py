#!/usr/bin/python

import datetime
import time
import re

from twisted.protocols import basic
from twisted.internet import defer
from twisted.internet import reactor

from zigutils import *
from Log import *

from NuVoZone import NuVoZone
from SqueezeWatchApp import app

class NuVoProtocol(basic.LineReceiver) :

	def __init__(self,sources) :
		self.enabled = False
		self.pending_restart = False
		
		self.sources = sources;
		self.source_strs = [str(x) for x in self.sources];

		self.source_data = {}
		for i in self.sources :
			# per-source data
			self.source_data[i] = {}
			self.source_data[i]['dispinfo'] = None
			self.source_data[i]['displines'] = None
			self.source_data[i]['playlist_repeat'] = None
			self.source_data[i]['playlist_shuffle'] = None

		self.favorites = {}

		self.zones = {}

		reactor.callLater(3,self.notifyTimer)

	def start(self) :
		self.enabled = True

		# if we're already connected and ready to go, now go out and query status of squeeze
		if self.pending_restart == True :
			self.pending_restart = False
			self.receivedRestart()

	def getSources(self) :
		return self.sources

	def getZone(self,zone) :
		return self.zones[zone]

	def getZones(self) :
		return self.zones

	def isValidZone(self,zone_num) :
		return zone_num in self.zones

	def notifyTimer(self) :
		"""
		Called about once a day to set the clock on the NuVo. Since we can only set H:M,
		we try to get called with the clock at zero seconds to make the time as accurate
		as possible on the NuVo.
		"""
		self.should_sync_time = True

		# first, work to get ourselves called right on a minute boundary
		now = datetime.now()
		if now.second == 0 :
			dlog('setting time to',now.year,',',now.month,',',now.day,',',now.hour,',',now.minute)
			if self.enabled and not self.pending_restart :
				self.send('*CFGTIME',now.year,',',now.month,',',now.day,',',now.hour,',',now.minute)
				self.should_sync_time = False
				# time is accurate, so let's get called back at around 3am to do it all again
				sleep_time = ((3-now.hour)*60+(59-now.minute))*60
				if sleep_time <= 0 :
					sleep_time += 24*60*60
				dlog("callback in",sleep_time,"seconds")
				reactor.callLater(sleep_time,self.notifyTimer)
				return
		else :
			dlog("got a timer on a non-minute boundary",now.second)

		reactor.callLater(60-(now.second + now.microsecond/1000000),self.notifyTimer)
		
	def lineReceived(self,line) :
		#dlog(line)
		line = str(line, "utf-8")
		if line == '#PING' :
			self.receivedPing()
			return
		if line == '#RESTART"Bridge"' :
			if not self.enabled :
				self.pending_restart = True
				return
			self.receivedRestart()
			return

		if not self.enabled :
			return

		if line == '#OK' :
			return
		if line == '#?' :
			elog("Received confused response from NuVoNet")
			return

		#dlog(line)

		m = re.match(r'#S(\d+).*',line)
		if m :
			(source,) = m.groups()
			if not source in self.source_strs :
				#dlog("received line about another source",line)
				return

		m = re.match(r'#Z(\d+)S(\d+)BUTTON(\d+),(\d+),(\d|0x[0-9A-F]+),(\d+),(\d+)',line)
		if m :
			self.receivedButton(m)
			return

		m = re.match(r'#Z(\d+)S(\d+)BUTTON(\d+),(\d+),(\d|0x[0-9A-F]+),(\d+),(\d+)',line)
		if m :
			self.receivedButton(m)
			return
		m = re.match(r'#Z(\d+)S(\d+)MENUREQ(\d+|0x[0-9A-F]+),(\d+),(\d+),(\d+)',line)
		if m :
			self.receivedMenuRequest(m)
			return
		m = re.match(r'#Z(\d+)S(\d+)MENUACTIVE(\d+|0x[0-9A-F]+),(\d+)',line)
		if m :
			self.receivedMenuActive(m)
			return
		m = re.match(r'#S(\d+)FAVORITE(\d+|0x[0-9A-F]+)$',line)
		if m :
			self.receivedFavorite(m)
			return
		m = re.match(r'#ALLOFF',line)
		if m :
			self.receivedAllOff(m)
			return
		m = re.match(r'#Z(\d+),OFF',line)
		if m :
			self.receivedZoneOff(m)
			return
		m = re.match(r'#Z(\d+),ON,SRC(\d+),VOL\d+,DND\d+,LOCK\d+',line)
		if m :
			self.receivedZoneOnSource(m)
			return
		m = re.match(r'#ZCFG(\d+),ENABLE0',line)
		if m :
			# zone is disabled, ignore
			return
		m = re.match(r'#ZCFG(\d+),ENABLE1,NAME"(.*)"',line)
		if m :
			self.receivedZoneConfigStatus(m)
			return
		dlog("unhandled:",line)

	def connectionMade(self) :
		dlog("connection made to NuVo")
		#self.send('*_DISABLEPING')
		self.send('*RESTART')

	def connectionLost(self,reason) :
		dlog("connection lost from NuVo")

	def getRepeatStatus(self,source) :
		return self.source_data[source]['playlist_repeat']

	def getShuffleStatus(self,source) :
		return self.source_data[source]['playlist_shuffle']

	def getNextRepeatStatus(self,source) :
		return (self.getRepeatStatus(source) + 1) % 3

	def getNextShuffleStatus(self,source) :
		return (self.getShuffleStatus(source) + 1) % 3

	def clearFavorites(self) :
		self.favorites = {}

	def answerStatus(self,source,data) :
		# perhaps should look at data['showBriefly']
		self.source_data[source]['playlist_repeat'] = int(data['playlist repeat'])
		self.source_data[source]['playlist_shuffle'] = int(data['playlist shuffle'])

		duration = 0
		if 'duration' in data :
			duration = int(10*float(data['duration']))
		position = 0
		if 'time' in data :
			position = int(10*float(data['time']))
		if duration == 0 and duration > 0:
			duration = 6000
		mode = 0
		if data['mode'] == 'play' :
			mode = 2
			if self.source_data[source]['playlist_repeat'] > 0 and self.source_data[source]['playlist_shuffle'] > 0 :
				mode = 8
			elif self.source_data[source]['playlist_repeat'] > 0 and self.source_data[source]['playlist_shuffle'] == 0 :
				mode = 7
			elif self.source_data[source]['playlist_repeat'] == 0 and self.source_data[source]['playlist_shuffle'] > 0 :
				mode = 6
			
		elif data['mode'] == 'stop' :
			mode = 0
		elif data['mode'] == 'pause' :
			mode = 3
		
		current_index = 0
		if 'playlist_cur_index' in data :
			current_index = int(data['playlist_cur_index']) + 1
		total_tracks = 0
		if 'playlist_tracks' in data :
			total_tracks = int(data['playlist_tracks'])
		progress = ''
		if total_tracks > 1 :
			progress = str(current_index) + ' of ' + str(total_tracks)

		#print data

		artist = ''
		if 'artist' in data :
			artist = data['artist']
		album = ''
		if 'album' in data :
			album = data['album']
		elif 'current_title' in data :
			album = data['current_title']
		title = ''
		if 'title' in data :
			title = data['title']

		any_changed = False

		if data['mode'] == 'stop' :
			displines = makeString('*S',source,'DISPLINES2,2,1,"','','","','','","','','","','','"')
			dispinfo = makeString('*S',source,'DISPINFO',0,',',0,',',mode)
		else :
			displines = makeString('*S',source,'DISPLINES2,2,1,"',progress,'","',album,'","',artist,'","',title,'"')
			if duration == 0 :
				# streaming causes this
				dispinfo = makeString('*S',source,'DISPINFO',0,',',0,',',mode)
				any_changed = True
			else :
				dispinfo = makeString('*S',source,'DISPINFO',duration,',',position,',',mode)

		if displines != self.source_data[source]['displines'] :
			any_changed = True
			self.send(displines)
			self.source_data[source]['displines'] = displines
	
		if dispinfo != self.source_data[source]['dispinfo'] :
			any_changed = True
			self.send(dispinfo)
			self.source_data[source]['dispinfo'] = dispinfo

		if any_changed :
			for (zone_num,zone) in self.zones.items() :
				if zone.getSource() == source :
					zone.notifyStatusChanged()

	def answerRepeatStatus(self,source,repeat_status) :
		self.source_data[source]['playlist_repeat'] = repeat_status

	def answerShuffleStatus(self,source,shuffle_status) :
		self.source_data[source]['playlist_shuffle'] = shuffle_status

	def answerFavorites(self,tuple_var) :
		favorites_data, = tuple_var
		if not self.enabled :
			return

		sources = []
		for i in range(1,7) :
			if i in self.sources :
				sources.append(str(1))
			else :
				sources.append(str(0))
		self.send('*S',str(self.sources[0]),'FAVORITES',len(favorites_data),',',','.join(sources))
		index = 0
		for (id,name) in favorites_data :
			index += 1
			self.favorites[index] = id
			self.send('*S',str(self.sources[0]),'FAVORITESITEM',index,',0,0,"',nuvoEscape(name),'"')

	def sendGetZoneStatus(self,zone_num) :
		self.send('*Z',zone_num,'STATUS?')

	def sendZoneOn(self,zone_num) :
		self.send('*Z',zone_num,'ON')

	def sendZoneOff(self,zone_num) :
		self.send('*Z',zone_num,'OFF')

	def sendAllOff(self) :
		self.send('*ALLOFF')

	def sendMenu(self,source,zone_num,menuid,menusize,selectiditemindex,firstblockitemindex,blocksize,description) :
		self.send('*S',source,'Z',zone_num,'MENU',menuid,',0,0,',menusize,',',selectiditemindex,',',firstblockitemindex,',',blocksize,',"',nuvoEscape(description),'"')

	def sendMenuItem(self,source,zone_num,itemid,itemtype,description) :
		self.send('*S',source,'Z',zone_num,'MENUITEM',itemid,',',itemtype,',0,"',nuvoEscape(description),'"')

	def sendExitMenu(self,source,zone_num) :
		self.send('*S',source,'Z',zone_num,'MENU0,0,0,0,0,0,0,""')

	def sendMainMenu(self,source,zone_num) :
		self.send('*S',source,'Z',zone_num,'MENU0xFFFFFFFF,0,0,0,0,0,0,""')

	def receivedRestart(self) :
		dlog("responding to restart")
		self.dispinfo = None
		self.displines = None

		# set the nuvo's time
		now = datetime.now()
		self.send('*CFGTIME',now.year,',',now.month,',',now.day,',',now.hour,',',now.minute)

		# tell it which sources we are controlling
		sources = []
		for i in range(1,7) :
			if i in self.sources :
				sources.append(str(1))
			else :
				sources.append(str(0))
		self.send('*SNUMBERS' + ','.join(sources))

		#set name
		source_index = 1
		for source in self.sources :
			source_str = str(source)
			self.send('*S' + source_str + 'NAME"SqueezeBox' + str(source_index) + '"')
			source_index += 1

		# setup menu
		self.sendTopLevelMenuItems()

		# get status of this source for display
		for source in self.sources :
			app.getStatus(source)

		# find out what zones are enabled
		for i in range(1,17) :
			self.send("*ZCFG",str(i),"STATUS?")

		d = defer.Deferred()
		d.addCallback(self.answerFavorites)
		app.getFavorites(d,0,20)

	def sendTopLevelMenuItems(self) :
		try :
			file = open("/tmp/weatherinfo.txt")
			line = file.readline().rstrip()
		except IOError as e:
			line = "Unknown info"

		for source in self.sources :
			source_str = str(source)
			self.send('*S' + source_str + 'MENU,5')
			self.send('*S' + source_str + 'MENUITEM1,1,0,"Artists"')
			self.send('*S' + source_str + 'MENUITEM2,1,0,"Playlists"')
			self.send('*S' + source_str + 'MENUITEM3,1,0,"New Music"')
			self.send('*S' + source_str + 'MENUITEM4,1,0,"Settings"')
			self.send('*S' + source_str + 'MENUITEM5,4,0,"' + line + '"')

	def receivedPing(self) :
		#print "responding to ping"
		self.send('*PING')
		self.sendTopLevelMenuItems()

	def receivedZoneConfigStatus(self,m) :
		(zone_num, name) = m.groups()
		zone_num = int(zone_num)
		self.zones[zone_num] = NuVoZone(self,zone_num,name)

	def receivedButton(self,m) :
		#print "got button"
		(zone_num, source, button, action, menuid, itemid, itemindex) = m.groups()
		if not source in self.source_strs :
			dlog("button for another device")
			return

		zone_num = int(zone_num)
		button = int(button)
		action = int(action)
		# convert menuid potentially from hex
		menuid = parseNumber(menuid)
		itemid = int(itemid)
		itemindex = int(itemindex)

		#print "zone_num",zone_num,"source",source,"button",button,"action",action,"menuid",menuid,"itemid",itemid,"itemindex",itemindex

		zone = self.zones[zone_num]
		zone.receivedButton(source,button,action,menuid,itemid,itemindex)

	def receivedMenuRequest(self,m) :
		#print "got menu request"
		(zone_num, source, menuid, up, location, itemindex) = m.groups()
		if not source in self.source_strs :
			dlog("menu request for another device")
			return

		zone_num = int(zone_num)
		# convert menuid potentially from hex
		menuid = parseNumber(menuid)
		up = int(up)
		location = int(location)
		itemindex = int(itemindex)
		#dlog("got menuid",menuid)

		#print "zone_num",zone_num,"source",source,"menuid",menuid,"up",up,"location",location,"itemindex",itemindex
		
		zone = self.zones[zone_num]
		zone.receivedMenuRequest(source,menuid,up,location,itemindex)

	def receivedMenuActive(self,m) :
		#print "got menu active"
		(zone_num, source, menuid, exit) = m.groups()
		if not source in self.source_strs :
			dlog("menu request for another device")
			return

		zone_num = int(zone_num)
		exit = int(exit)
		#print "zone_num",zone_num,"source",source,"menuid",menuid,"exit",exit
		zone = self.zones[zone_num]
		zone.receivedMenuActive(exit)

	def receivedFavorite(self,m) :
		(source, menuid) = m.groups()
		#dlog("got favorite",source,menuid)
		source = int(source)
		menuid = parseNumber(menuid)
		favoriteid = self.favorites[menuid]
		app.playFavorite(source,favoriteid)

	def receivedAllOff(self,m) :
		dlog("received all off")
		for source in self.sources :
			app.pause(source)
			app.powerOff(source)

	def receivedZoneOff(self,m) :
		(zone_num,) = m.groups()
		zone_num = int(zone_num)
		#dlog("received zone",zone_num,"off")
		zone = self.zones[zone_num]
		source = zone.getSource()
		zone.receivedOff()
		# auto-pause if we just lost the last zone listening to a source
		if source in self.sources :
			if not self.isAnyZoneOnThisSource(source) :
				app.pause(source)
				# should possibly turn off hardware sources, but not softsqueeze here...
				#app.powerOff(source)

	def receivedZoneOnSource(self,m) :
		(zone_num, source) = m.groups()
		zone_num = int(zone_num)
		source = int(source)
		#dlog("received zone",zone_num,"on source",source)
		zone = self.zones[zone_num]
		zone.receivedOnSource(source)
		# auto-pause if no one listening
		if not self.isAnyZoneOnThisSource(source) :
			app.pause(source)

	def isAnyZoneOnThisSource(self,source) :
		for (zone_num,zone) in self.zones.items() :
			if zone.getSource() == source :
				return True
		return False

	def send(self,*args) :
		s = ''.join([str(arg) for arg in args])
		if not self.transport :
			dlog("can't send to NuVo when we don't have a transport")
			return
		dlog("sending",s)
		self.transport.write(s.encode('ascii', errors='ignore'))
		self.transport.write(b'\r')
		time.sleep(0.002)
