#!/usr/bin/python

from twisted.internet.protocol import Factory
from twisted.internet import reactor

from twisted.web.server import Site

from twisted.internet.serialport import SerialPort

from Log import *

from SqueezeWatchApp import SqueezeWatchApp, app

from SqueezeCLIFactory import SqueezeCLIFactory
from SqueezeCLIProtocol import SqueezeCLIProtocol

from NuVoProtocol import NuVoProtocol

from RequestRoot import RequestRoot

def Init(*args) :
	Log.init(*args)


def Run() :
	log("starting app")

	app.nuvo_protocol = NuVoProtocol((3,5))
	# there are more serial settings that are correct on boot, but
	# some apps can change them. We should set more here. If you have
	# problems talking serial, try rebooting
	#serport = SerialPort(app.nuvo_protocol,"/dev/ttyUSB0",reactor,baudrate=57600)
	serport = SerialPort(app.nuvo_protocol,"/dev/ttyS0",reactor,baudrate=57600)

	# listen to incoming maintenance text connections
	app.factory = SqueezeCLIFactory()
	app.factory.protocol = SqueezeCLIProtocol

	reactor.connectTCP("192.168.2.10",9090,app.factory)
	#reactor.connectTCP("localhost",9090,app.factory)
	#reactor.connectTCP("mario",9090,app.factory)

	factory = Site(RequestRoot())
	reactor.listenTCP(8000,factory)

	reactor.run()


Init()
Run()

