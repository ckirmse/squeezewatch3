#!/usr/bin/python

from zigutils import *

from datetime import datetime

class Log :

	log_file = None
	elog_file = None
	dlog_file = None
	log_stdout = True

	@classmethod
	def init(cls,filename=None) :
		if filename :
			cls.log_file = open(filename,'a')
			cls.elog_file = cls.log_file
			cls.dlog_file = cls.log_file
			cls.log_stdout = False
		else :
			cls.log_file = open("log.txt",'a')
			cls.elog_file = open("error.txt",'a')
			cls.dlog_file = open("debug.txt",'a')
			cls.log_stdout = True


	@classmethod
	def log(cls,*args) :
		s = cls.buildString(*args)
		cls.log_file.write(s + "\n")
		if cls.log_stdout :
			print s
		else :
			cls.log_file.flush()

	@classmethod
	def elog(cls,*args) :
		s = cls.buildString(*args)
		cls.elog_file.write(s + "\n")
		if cls.log_stdout :
			print s
		else :
			cls.elog_file.flush()

	@classmethod
	def dlog(cls,*args) :
		s = cls.buildString(*args)
		cls.dlog_file.write(s + "\n")
		if cls.log_stdout :
			print s
		else :
			cls.dlog_file.flush()

	@classmethod
	def buildString(cls,*args) :
		date_str = datetime.now().strftime("%b %e %Y %H:%M:%S")
		func_str = Func(3)
		s = date_str + ' ' + func_str + ' ' + ' '.join(map(str,args))
		return s

def elog(*args) :
	Log.elog(*args)

def dlog(*args) :
	Log.dlog(*args)

def log(*args) :
	Log.log(*args)
	
