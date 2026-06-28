#!/usr/bin/python

import asyncio
import os
import sys

import uvicorn

from Log import *

from SqueezeWatchApp import SqueezeWatchApp, app

from SqueezeCLIFactory import SqueezeCLIFactory
from SqueezeCLIProtocol import SqueezeCLIProtocol

from NuVoProtocol import NuVoProtocol

from RequestHTML import http_app


def Init(*args) :
	Log.init(*args)


async def connect_lms(factory) :
	loop = asyncio.get_running_loop()
	delay = 5
	while True :
		try :
			log("Connecting to LMS...")
			proto = SqueezeCLIProtocol(factory)
			await loop.create_connection(lambda: proto, 'mario', 9090)
			await proto.waitDisconnected()
			log("LMS connection lost, will reconnect")
		except OSError as e :
			log("LMS connect failed:", e)
		await asyncio.sleep(delay)


async def main() :
	loop = asyncio.get_running_loop()

	cmd_folder = os.path.dirname(os.path.abspath("templates/home.py"))
	if cmd_folder not in sys.path :
		sys.path.insert(0, cmd_folder)

	app.lms_host = 'mario'

	app.player_source_map = {
		'00:27:0e:05:73:68': 3,
		'00:22:6c:36:3d:26': 5,
	}
	app.nuvo_protocol = NuVoProtocol((5,3))

	app.factory = SqueezeCLIFactory()
	asyncio.ensure_future(connect_lms(app.factory))

	import serial_asyncio
	try :
		await serial_asyncio.create_serial_connection(
			loop, lambda: app.nuvo_protocol, '/dev/ttyS0', baudrate=57600)
	except Exception as e :
		log("Serial port unavailable:", e)

	config = uvicorn.Config(http_app, host='0.0.0.0', port=8000, log_level='warning')
	server = uvicorn.Server(config)
	await server.serve()


Init()
asyncio.run(main())
