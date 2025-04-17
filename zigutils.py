#!/usr/bin/python

import re
import inspect

# num is a string which may or may not be in hex
def parseNumber(num) :
	hexmap = { '0' : 0, '1':1,'2':2,'3':3,'4':4,'5':5,'6':6,'7':7,'8':8,'9':9,
			   'A':10,'B':11,'C':12,'D':13,'E':14,'F':15 }
	m = re.match(r'0x[0-9A-F]',num)
	if m :
		# convert from hex
		retval = hexmap[num[2]]
		for i in num[3:] :
			retval = retval*16 + hexmap[i]
		return retval
	# not hex, assume decimal
	return int(num)

def makeString(*args) :
	return ''.join([str(s) for s in args])

def nuvoEscape(s) :
	retval = []
	for ch in s.encode("ISO-8859-1") :
		if ch >= 128 :
			retval.append('_')
		elif ch == ord('*') :
		#if ch == '*' :
			retval.append(r'\*')
		elif ch == ord('"') :
			retval.append(r'\"')
		else :
			retval.append(chr(ch))
	return ''.join(retval)

def Func(base_level=0) :
	"""returns function name that called this; can pass in a count of how far up stack
	to go"""
	level = base_level + 1
	# first check if we have an object to print out the class name
	args, varargs, varkw, defaults = inspect.getargvalues(inspect.stack()[level][0])
	prefix = ""
	if 'self' in defaults :
		prefix = defaults['self'].__class__.__name__ + "."

	return prefix + inspect.stack()[level][3] + "()"

def FileLine() :
	"returns filename and line number that called this"
	return inspect.stack()[1][1] + " " + inspect.stack()[1][2]
