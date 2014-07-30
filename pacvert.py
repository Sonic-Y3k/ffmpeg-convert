#!/usr/bin/python2

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
import random # Generating a random numbers.
import errno  # Error numbers

from sys import argv          # Command-line arguments
from sys import stdout, stdin # Flushing

from shutil import copy # Copying iles

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

if not os.uname()[0].startswith("Linux") and not 'Darwin' in os.uname()[0]:
	print (O+' [!]'+R+' WARNING:'+G+' Pacvert'+W+' must be run on '+O+'Linux/OSX'+W)
	exit(1)
	
# Create temporary directory to work in
from tempfile import mkdtemp
temp = mkdtemp(prefix='pacvert')
if not temp.endswith(os.sep):
	temp += os.sep
	
# /dev/null, send output from programs so they don't print to screen.
DN = open(os.devnull, 'w')

###################
# DATA STRUCTURES #
###################

class StreamInfo:
	"""
		Holds data for a Stream
	"""
	def __init__(self, id, codecName, language, channels):
		self.id			= id
		self.codecName	= codecName
		self.language	= language
		self.channels	= channels

##################
# MAIN FUNCTIONS #
##################

def banner():
	"""
		Displays ASCII art
	"""
	global VERSION
	print ("")
	print (R+"      :;;;;;;;;;:    ")
	print (R+"    :;;;;;;;;;;;;:   ")
	print (R+"   ;;;;;;;;;;;;;;::  ")
	print (R+"   ;;;;;;;;;;;;;;;;; ")
	print (R+"  ;;;;;;``;;;; ;;;;; "+W+"Pacvert v"+str(VERSION))
	print (R+"  ;;;;;` ' ;;  ';;;; ")
	print (R+"  ;;;;;  +,;; :+;;;; "+GR+"Automated video conversion")
	print (R+"  ;;;;;;  ;;;` `;;;; ")
	print (R+"  ;;;;;;;;;;;;;;;;;; "+GR+"Designed for Linux/OSX")
	print (R+"  ;;;;;;;;;;;;;;;;;; ")
	print (R+"  ;;;;;;;;;;;;;;;;;; ")
	print (R+"  ;;;  ;;;; ;;;;`';;  ")
	print (R+"  ;;    ;;   ;;`  ;;  ")
	print (W)

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
	start	= page.find("VERSION")
	if start != -1:
		page	= page[start+10:len(page)]
		page	= page[0:page.find(";")]
		try:
			rver= float(page)
		except ValueError:
			rver=page.split('\n')[0]
			print (R+" [!] invalid version number: '"+page+"'")

	return rver

def upgrade():
	"""
		Checks for new Version, promts to upgrade, then
		replaces this script with the latest from the repo.
	"""
	global VERSION
	try:
		print (GR+" [!]"+W+" upgrading requires an "+R+"internet connection"+W)
		print (GR+" [+]"+W+" checking for latest version..."+W)
		remote_version = get_remote_version()

		if remote_version == -1:
			print (R+" [!]"+O+" unable to access github"+W)
		elif remote_version > float(VERSION):
			print (GR+" [!]"+W+" version "+G+str(remote_version)+W+" is "+G+"available!"+W)
			response = raw_input(GR+" [+]"+W+" do you want to upgrade to the latest version? (y/n): ")
			if not response.lower().startswith("y"):
				print (GR+" [-]"+W+" upgrading "+O+"aborted"+W)
				return

			#Download script and replace this one
			print (GR+" [+] "+G+"downloading"+W+" update...")
			try:
				sock = urllib2.urlopen("https://raw.githubusercontent.com/Sonic-Y3k/ffmpeg-convert/master/pacvert.py")
				page = sock.read()
			except IOError:
				page = ''

			if page == '':
				print (R+' [+] '+O+'unable to download latest version'+W)
				exit_gracefully(1)

			# Create/save the new script
			f=open('pacvert_new.py','w')
			f.write(page)
			f.close()

			# The filename of the running script
			this_file = __file__
			if this_file.startswith('./'):
				this_file = this_file[2:]

			# create/save a shell script that replaces this script with the new one
			f = open('update_pacvert.sh','w')
			f.write('''#!/bin/sh\n
				rm -rf ''' + this_file + '''\n
				mv pacvert_new.py ''' + this_file + '''\n
				rm -rf update_pacvert.sh\n
				chmod +x ''' + this_file + '''\n
				''')
			f.close()

			# Change permissions on the script
			returncode = call(['chmod','+x','update_pacvert.sh'])
			if returncode != 0:
				print (R+' [!]'+O+' permission change returned unexpected code: '+str(returncode)+W)
				exit_gracefully(1)

			# Run the script
			returncode = call(['sh','update_pacvert.sh'])
			if returncode != 0:
				print (R+' [!]'+O+' upgrade script returned unexpected code: '+str(returncode)+W)
				exit_gracefully(1)

			print (GR+' [+] '+G+'updated!'+W+' type "./' + this_file + '" to run again')
		else:
			print (GR+' [-]'+W+' your copy of Pacvert is '+G+'up to date'+W)

	except KeyboardInterrupt:
		print (R+'\n (^C)'+O+' Pacvert upgrade interrupted'+W)
		exit_gracefully(0)

def program_exists(program):
	"""
		Uses 'which' (linux command) to check if a program is installed.
	"""  
	proc = Popen(['which', program], stdout=PIPE, stderr=PIPE)
	txt = proc.communicate()
	if txt[0].strip() == '' and txt[1].strip() == '':
		return False
	if txt[0].strip() != '' and txt[1].strip() == '':
		return True
        
	return not (txt[1].strip() == '' or txt[1].find('no %s in' % program) != -1)

def initial_check():
	"""
		Ensures required programs are installed.
	"""
	ffmpegs = ["ffmpeg", "ffprobe"]
	for ffmpeg in ffmpegs:
		if program_exists(ffmpeg): continue
		print (R+" [!]"+O+" required program not found: %s" % (R+ffmpeg+W))
		if program_exists("brew"):
			print (R+"    "+O+"   install with "+C+"brew install ffmpeg"+W)
		else:
			print (R+"    "+O+"   available at "+C+"https://ffmpeg.org/"+W)
		exit_gracefully(1)
		
	if not program_exists("mplayer"):
		print (R+" [!]"+O+" required program not found: mplayer"+W)
		if program_exists("brew"):
			print (R+"    "+O+"   install with "+C+"brew install mplayer"+W)
		else:
			print (R+"    "+O+"   available at "+C+"http://mplayerhq.hu/"+W)
		exit_gracefully(1)
	
	if not program_exists("mkvextract"):
		print (R+" [!]"+O+" required program not found: mkvextract"+W)
		print (R+"    "+O+"   this tool is part of the mkvtoolnix suite"+W)
		if program_exists("brew"):
			print (R+"    "+O+"   install with "+C+"brew install mkvtoolnix"+W)
		else:
			print (R+"    "+O+"   available at "+C+"http://bunkus.org/videotools/mkvtoolnix/"+W)
		exit_gracefully(1)
		
	if not program_exists("bdsup2sub"):
		print (R+" [!]"+O+" required program not found: bdsup2sub"+W)
		if program_exists("brew"):
			print (R+"    "+O+"   install with "+C+"brew install https://raw.githubusercontent.com/Sonic-Y3k/homebrew/master/bdsup2sub++.rb"+W)
		else:
			print (R+"    "+O+"   available at "+C+"http://forum.doom9.org/showthread.php?p=1613303"+W)
		exit_gracefully(1)
	
	transcodes = ["tcextract", "subtitle2pgm", "srttool"]
	for transcode in transcodes:
		if program_exists(transcode): continue
		print (R+" [!]"+O+" required program not found: %s" % (R+transcode+W))
		print (R+"    "+O+"   this tool is part of the transcode suite"+W)
		if program_exists("brew"):
			print (R+"    "+O+"   install with "+C+"brew install https://raw.githubusercontent.com/Sonic-Y3k/homebrew/master/transcode.rb"+W)
		else:
			print (R+"    "+O+"   available at "+C+"http://www.linuxfromscratch.org/blfs/view/svn/multimedia/transcode.html"+W)
		exit_gracefully(1)
	
	if not program_exists("tesseract"):
		print (R+" [!]"+O+" required program not found: tesseract"+W)
		if program_exists("brew"):
			print (R+"    "+O+"   install with "+C+"brew install tesseract --all-languages"+W)
		else:
			print (R+"    "+O+"   available at "+C+"http://code.google.com/p/tesseract-ocr/"+W)
			print (R+"    "+O+"   please install with "+C+"all"+W+" available language packs.")
		exit_gracefully(1)
	
	if not program_exists("vobsub2srt"):
		print (R+" [!]"+O+" required program not found: vobsub2srt"+W)
		if program_exists("brew"):
			print (R+"    "+O+"   install with "+C+"brew install https://raw.githubusercontent.com/ruediger/VobSub2SRT/master/packaging/vobsub2srt.rb --HEAD vobsub2srt"+W)
		else:
			print (R+"    "+O+"   available at "+C+"https://github.com/ruediger/VobSub2SRT"+W)
		exit_gracefully(1)
	
	if not program_exists("jsawk"):
		print (R+" [!]"+O+" required program not found: jsawk"+W)
		if program_exists("brew"):
			print (R+"    "+O+"   install with "+C+"brew install jsawk"+W)
		else:
			print (R+"    "+O+"   available at "+C+"http://github.com/micha/jsawk"+W)
		exit_gracefully(1)

def exit_gracefully(code=0):
	"""
		May exit the program at any given time.
	"""
	# Remove temp files and folder
	if os.path.exists(temp):
		for file in os.listdir(temp):
			os.remove(temp + file)
		os.rmdir(temp)
	print (R+" [+]"+W+" quitting") # pacman will now exit"
	print ''
	# GTFO
	exit(code)

if __name__ == '__main__':
	try:
		banner()
		upgrade()
		initial_check()

	except KeyboardInterrupt: print (R+'\n (^C)'+O+' interrupted\n'+W)
	except EOFError:          print (R+'\n (^D)'+O+' interrupted\n'+W)

	exit_gracefully(0)