#!/usr/bin/python

# -*- coding: utf-8 -*-

"""
	Convert with Pacman
	
	author: sonic.y3k at googlemail
	
	(c) 2014
"""

#############
# LIBRARIES #
#############

import os     # File management
import time   # Measuring attack intervals
import random # Generating a random MAC address.
import errno  # Error numbers

from sys import argv          # Command-line arguments
from sys import stdout, stdin # Flushing

from shutil import copy # Copying .cap files

# Executing, communicating with, killing processes
from subprocess import Popen, call, PIPE
from signal import SIGINT, SIGTERM

import urllib2 # Check for new versions from the repo

################################
# Global Variables in all caps #
################################

VERSION = 1.9;

# Console colors
W  = '\033[0m'  # white (normal)
R  = '\033[31m' # red
G  = '\033[32m' # green
O  = '\033[33m' # orange
B  = '\033[34m' # blue
P  = '\033[35m' # purple
C  = '\033[36m' # cyan
GR = '\033[37m' # gray

##################
# MAIN FUNCTIONS #
##################

def banner():
	"""
		Displays ASCII art
	"""
	global VERSION
	print ''
	print R+"      :;;;;;;;;;:    "
	print R+"    :;;;;;;;;;;;;:   "
	print R+"   ;;;;;;;;;;;;;;::  "
	print R+"   ;;;;;;;;;;;;;;;;; "
	print R+"  ;;;;;;``;;;; ;;;;; "+W+"Pacvert v"+str(VERSION)
	print R+"  ;;;;;` ' ;;  ';;;; "
	print R+"  ;;;;;  +,;; :+;;;; "+GR+"Automated video conversion"
	print R+"  ;;;;;;  ;;;` `;;;; "
	print R+"  ;;;;;;;;;;;;;;;;;; "+GR+"Designed for Linux/OSX"
	print R+"  ;;;;;;;;;;;;;;;;;; "
	print R+"  ;;;;;;;;;;;;;;;;;; "
	print R+"  ;;;  ;;;; ;;;;`';;  "
	print R+"  ;;    ;;   ;;`  ;;  "
	print W

def get_remote_version():
	"""
		Gets the latest remote version from github repository
		Returns: newest version
	"""
	rver = -1
	try:
		sock = urllib2.urlopen("https://raw.githubusercontent.com/Sonic-Y3k/ffmpeg-convert/master/pacvert.py")
		page = sock.read()
	except IOError:
		return -1
		
	#Get the version
	start	= page.find("VERSION = ")
	if start != -1:
		start	+= 10
		rev		= page[start:";\n"]
		try:
			iver= int(rev)
		except ValueError:
			rev=rev.split('\n')[0]
			print R+"[+] invalid version number: '"+rev+"'"
			
	return iver

def upgrade():
	"""
		Checks for new Version, promts to upgrade, then
		replaces this script with the latest from the repo.
	"""
	global VERSION
	try:
		print GR+" [!]"+W+" upgrading requires an "+R+"internet connection"+W
		print GR+" [+]"+W+" checking for latest version..."
		remote_version = get_remote_version()
	except KeyboardInterrupt:
		print R+'\n (^C)'+O+' Pacvert upgrade interrupted'+W
		exit_gracefully(0)
		
def exit_gracefully(code=0):
	"""
		May exit the program at any given time.
	"""
	print R+" [+]"+W+" quitting" # pacman will now exit"

if __name__ == '__main__':
	try:
		banner()
		upgrade()
	
	except KeyboardInterrupt: print R+'\n (^C)'+O+' interrupted\n'+W
	except EOFError:          print R+'\n (^D)'+O+' interrupted\n'+W
	
	exit_gracefully(0)