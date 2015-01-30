#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    Convert with Pacman

    author: sonic.y3k at googlemail dot com

    Licensed under the GNU General Public License Version 2 (GNU GPL v2),
    available at: http://www.gnu.org/licenses/gpl-2.0.txt

    (c) 2014-2015
"""

################################
# Global Variables in all caps #
################################

# Version
VERSION = 4.0;
DATE = "29.01.2015";

# Console colors
W  = '\033[0m'  # white (normal)
R  = '\033[31m' # red
G  = '\033[32m' # green
O  = '\033[33m' # orange
B  = '\033[34m' # blue
P  = '\033[35m' # purple
C  = '\033[36m' # cyan
GR = '\033[37m' # gray

#############
# Libraries #
#############

import os
import sys
import re
import fcntl
import time
import signal
import argparse
from subprocess import Popen, call, PIPE, check_output, CalledProcessError
from sys import stdout, stdin

try:
	import configparser
except ImportError:
	import ConfigParser as configparser
	
try:
    from progressbar import *
except ImportError:
    print("Please install progressbar2 first.")
    print("sudo pip install progressbar2")
    exit(1)

DN = open(os.devnull,'w')

###################
# Data Structures #
###################

class PacvertError(Exception):
    def __init__(self, message, cmd=None, output=None, details=None, pid=0):
        """
        @param message: Error message.
        @type message: C{str}

        @param cmd: Full command string used to spawn ffmpeg.
        @type cmd: C{str}

        @param output: Full stdout output from the ffmpeg command.
        @type output: C{str}

        @param details: Optional error details.
        @type details: C{str}
        """
        super(PacvertError, self).__init__(message)
        self.cmd = cmd
        self.output = output
        self.details = details
        self.pid = pid

    def __repr__(self):
        error = self.details if self.details else self.message
        return ('<PacvertError error="%s", pid=%s, cmd="%s">' % (error, self.pid, self.cmd))

    def __str__(self):
        return self.__repr__()

class Pacvert():
	"""
		Main Class
	"""
	def __init__(self):
		#Create temp directory
		self.create_temp()

		#Handle CLI Args
		self.handle_args()

		# Initialize Banner
		self.banner()
	
		#Check for Unix Systems
		if self.getPlatfrom() != "Linux" and self.getPlatfrom() != "Darwin":
			self.message("Only Linux/Darwin is currently supported.",2)
			self.exit_gracefully(1)

		#Load or create config
		self.loadConfigFile()

		#Set output directory
		try:
			self.OUTDIR = self.OUTDIR
		except:
			self.OUTDIR = os.getcwd()+"/output"

		#Begin dependency check
		self.checkDependencies()

		#misc
		self.message("Miscellaneous Informations:")
		self.message(O+"  * "+W+"Current Directory:\t"+os.getcwd())
		self.message(O+"  * "+W+"Output Directory:\t"+self.OUTDIR)
		self.message(O+"  * "+W+"Temporary Directory:\t"+self.TEMP)

		#Check for updates
		self.upgrade()

		try:
			self.FORCEDTS = self.FORCEDTS
			self.message("Forcing DTS-Audio!",1)
			self.message("This will be ignored with m4v files.",1)
		except AttributeError:
			self.FORCEDTS = False;

		try:
			self.FORCEX265 = self.FORCEX265
			self.message("Forcing x265-Encoder!",1)
			self.message("This will be ignored with m4v files.",1)
		except AttributeError:
			self.FORCEX265 = False;

		#Exit
		self.exit_gracefully()
	
	def create_temp(self):
		"""
			Creates temporary directory
		"""
		from tempfile import mkdtemp
		self.TEMP = mkdtemp(prefix='pacvert')
		if not self.TEMP.endswith(os.sep):
			self.TEMP += os.sep

	def program_exists(self,program):
		"""
			Uses "wich" (linux command) to check if a program is installed
		"""
		proc = Popen(["which",program], stdout=PIPE, stderr=PIPE,universal_newlines=True)
		txt = proc.communicate()
		return txt[0].strip()   

	def checkDependencies(self):
		"""
			Check for runtime dependencies
		"""
		self.message("Programs used:")
		self.tools = {}

		#ffmpeg
		self.tools["ffmpeg"] = self.program_exists("ffmpeg")
		if self.tools["ffmpeg"]:
			proc = Popen(["ffmpeg","-version"], stdout=PIPE, stderr=PIPE,universal_newlines=True)
			txt = proc.communicate()[0].strip().split(" ")[2]
			self.message(O+"  * "+W+"FFmpeg:\t"+txt)
		else:
			self.message("Required program not found: "+C+"ffmpeg"+W+".",2)
			self.exit_gracefully(1)

		#ffprobe
		self.tools["ffprobe"] = self.program_exists("ffprobe")
		if self.tools["ffprobe"]:
			proc = Popen(["ffprobe","-version"], stdout=PIPE, stderr=PIPE,universal_newlines=True)
			txt = proc.communicate()[0].strip().split(" ")[2]
			self.message(O+"  * "+W+"FFprobe:\t"+txt)
		else:
			self.message("Required program not found: "+C+"ffprobe"+W+".",2)
			self.exit_gracefully(1)

		#mplayer
		self.tools["mplayer"] = self.program_exists("mplayer")
		if self.tools["mplayer"]:
			proc = Popen(["mplayer"], stdout=PIPE, stderr=PIPE,universal_newlines=True)
			txt = proc.communicate()[0].strip().split(" ")[1]
			self.message(O+"  * "+W+"MPlayer:\t"+txt)
		else:
			self.message("Required program not found: "+C+"mplayer"+W+".",2)
			self.exit_gracefully(1)

		#mkvextract
		self.tools["mkvextract"] = self.program_exists("mkvextract")
		if self.tools["mkvextract"]:
			proc = Popen(["mkvextract","--version"], stdout=PIPE, stderr=PIPE,universal_newlines=True)
			txt = proc.communicate()[0].strip().split(" ")[1].replace("v","")
			self.message(O+"  * "+W+"MKVExtract:\t"+txt)
		else:
			self.message("Required program not found: "+C+"mkvextract"+W+".",2)
			self.exit_gracefully(1)

		#mediainfo
		self.tools["mediainfo"] = self.program_exists("mediainfo")
		if self.tools["mediainfo"]:
			proc = Popen(["mediainfo","--version"], stdout=PIPE, stderr=PIPE,universal_newlines=True)
			txt = proc.communicate()[0].strip().split(" ")[5].replace("v","")
			self.message(O+"  * "+W+"MediaInfo:\t"+txt)
		else:
			self.message("Required program not found: "+C+"mediainfo"+W+".",2)
			self.exit_gracefully(1)

		#bdsup2subpp
		self.tools["bdsup2subpp"] = self.program_exists("bdsup2subpp")
		if self.tools["bdsup2subpp"]:
			proc = Popen(["bdsup2subpp","--help"], stdout=PIPE, stderr=PIPE,universal_newlines=True)
			txt = proc.communicate()[0].strip().split(" ")[1].replace("v","")
			self.message(O+"  * "+W+"bdsup2sub++:\t"+txt)
		else:
			self.message("Required program not found: "+C+"bdsup2subpp"+W+".",2)
			self.exit_gracefully(1)

		#tesseract
		self.tools["tesseract"] = self.program_exists("tesseract")
		if self.tools["tesseract"]:
			proc = Popen(["tesseract","--version"], stdout=PIPE, stderr=PIPE,universal_newlines=True)
			txt = proc.communicate()[1].strip().split(" ")[1].replace("\n","")
			self.message(O+"  * "+W+"Tesseract:\t"+txt)
		else:
			self.message("Required program not found: "+C+"tesseract"+W+".",2)
			self.exit_gracefully(1)

		#vobsub2srt
		self.tools["vobsub2srt"] = self.program_exists("vobsub2srt")
		if self.tools["vobsub2srt"]:
			self.message(O+"  * "+W+"VobSub2SRT:\t1.0")
		else:
			self.message("Required program not found: "+C+"vobsub2srt"+W+".",2)
			self.exit_gracefully(1)

	def loadConfigFile(self):
		"""
			Loads the Config-File
		"""
		self.config = configparser.ConfigParser();
		if os.path.exists(self.getConfigPath()):
			#Config exists, very good!
			self.config.read(self.getConfigPath())

			#Check if config is deprecated
			if self.config.getfloat("ConfigVersion","Version") < VERSION:
				self.message("Your config is deprecated.",1)
				self.message("Your config will be reset to defaults.",1)

				try:
					#Remove old config file
					os.remove(self.getConfigPath())
				except PermissionError:
					self.message("Can't open config file \""+O+self.getConfigPath()+W+"\". Permission Denied.", 2)

				#Recreate configuration file
				self.loadConfigFile()
		else:
			#Config does not exists... we need to create.
			
			#Set Config Version
			self.config.add_section("ConfigVersion")
			self.config.set("ConfigVersion","Version",str(VERSION))

			#General File Settings
			self.config.add_section("FileSettings")
			self.config.set("FileSettings", "DeleteFile","True")
			self.config.set("FileSettings", "FileFormat", "")
			
			#Video Settings
			self.config.add_section("VideoSettings")
			self.config.set("VideoSettings","CRF","18.0")
			self.config.set("VideoSettings","CROP", "True")
			self.config.set("VideoSettings","X264Level","4.1")
			self.config.set("VideoSettings","X264Preset","slow")
			self.config.set("VideoSettings","X264Profile","high")
			self.config.set("VideoSettings","X264Tune","film")
			self.config.set("VideoSettings","X265Preset","slow")
			self.config.set("VideoSettings","X265Tune","")
			self.config.set("VideoSettings","X265Params","")
			
			#Audio Settings
			self.config.add_section("AudioSettings")
			self.config.set("AudioSettings","DefaultAudioCodec","")
			if self.getPlatfrom() == "Linux":
				self.config.set("AudioSettings","AACLib","aac -strict -2")
			elif self.getPlatform() == "Darwin":
				self.config.set("AudioSettings","AACLib","libfaac")
			self.config.set("AudioSettings","AC3Lib","ac3")
			self.config.set("AudioSettings","DTSLib","dca -strict -2")
			
			#Write config to file
			try:
				cfgfile = open(self.getConfigPath(),'w')
				self.config.write(cfgfile)
				cfgfile.close()
				self.message("Successfully configured \""+O+self.getConfigPath()+W+"\". Please relaunch")
			except PermissionError:
				self.message("Can't open config file \""+O+self.getConfigPath()+W+"\". Permission Denied.", 2)
			
			#Exit
			self.exit_gracefully(1)
	
	def getConfigPath(self):
		"""
			Returns the OS-Dependant config filepath
		"""
		if self.getPlatfrom() == "Linux":
			return "/etc/pacvert.conf"
		elif self.getPlatfrom() == "Darwin":
			return "/usr/local/etc/pacvert.conf"
	
	def getPlatfrom(self):
		"""
			Returns the platform this script is runing on
		"""
		if os.uname()[0].startswith("Linux"):
			return "Linux"
		elif "Darwin" in os.uname()[0]:
			return "Darwin"
		else:
			self.message("Unsupported Platform.",2)
			exit_gracefully(1)
	
	def message(self, mMessage, mType = 0):
		if mType == 0:
			print(G+" [+] "+W+mMessage+W)
		elif mType == 1:
			print(O+" [-] WARNING: "+W+mMessage+W)
		elif mType == 2:
			print(R+" [!] ERROR: "+W+mMessage+W)
		else:
			self.exit_gracefully(1)
	
	def get_remote_version(self):
		"""
			Get remote version from github
		"""
		rver = -1
		try:
			import urllib.request
			sock = urllib.request.urlopen("https://raw.githubusercontent.com/Sonic-Y3k/ffmpeg-convert/master/pacvert.py")
			page = str(sock.read()).strip()
		except ImportError:
			import urllib2
			sock = urllib2.urlopen("https://raw.githubusercontent.com/Sonic-Y3k/ffmpeg-convert/master/pacvert.py")
			page = str(sock.read()).strip()
		except IOError:
			return -1
		
		start = page.find("VERSION")
		if start != -1:
			page    = page[start+10:len(page)]
			page    = page[0:page.find(";")]
			try:
				rver= float(page)
			except ValueError:
				rver=page.split('\n')[0]
				self.message(O+"  * "+W+"Invalid remote version number", 2)
		return rver
	
	def upgrade(self):
		"""
			checks for new version
			and upgrades if necessary
		"""
		try:
			remote_version = self.get_remote_version()
			if remote_version == -1:
				self.message(O+"  * "+W+"Unable to access github.",2)
			elif remote_version > float (VERSION):
				self.message(O+"  * "+W+"Version "+G+str(remote_version)+W+" is "+G+"available!"+W)
				try:
					response = raw_input(G+" [+]"+O+"   * "+W+"do you want to upgrade to the latest version? (y/n): ")
				except NameError:
					response = input(G+" [+]"+O+"   * "+W+"do you want to upgrade to the latest version? (y/n): ")
				if not response.lower().startswith("y"):
					self.message("Upgrading aborted",1)
					return
				self.message(O+"  * "+W+"Downloading update...")
				try:
					import urllib.request
					sock = urllib.request.urlretrieve("https://raw.githubusercontent.com/Sonic-Y3k/ffmpeg-convert/master/pacvert.py","pacvert_new.py")
				except ImportError:
					import urllib2
					sock = urllib2.urlopen("https://raw.githubusercontent.com/Sonic-Y3k/ffmpeg-convert/master/pacvert.py")
					data = sock.read()
					with open("pacvert_new.py", "wb") as code:
						code.write(data)
				except IOError:
					self.message(O+"  * "+W+"Unable to download latest version",2)
					self.exit_gracefully(1)
				
				this_file = __file__
				if this_file.startswith('./'):
					this_file = this_file[2:]
				try:
					f = open('update_pacvert.sh','w')
					f.write('''#!/bin/sh\n
						rm -rf ''' + this_file + '''\n
						mv pacvert_new.py ''' + this_file + '''\n
						rm -rf update_pacvert.sh\n
						chmod +x ''' + this_file + '''\n
						''')
					f.close()
				except PermissionError:
					self.message(O+"  * "+W+"Can't open file \""+O+"update_pacvert.sh"+W+"\" for writing. Permission Denied.", 2)
					self.exit_gracefully(1)

				returncode = call(['chmod','+x','update_pacvert.sh'])
				if returncode != 0:
					self.message(O+"  * "+W+"Permission change returned unexpected code: "+str(returncode), 2)
					self.exit_gracefully(1)
				
				returncode = call(['sh','update_pacvert.sh'])
				if returncode != 0:
					self.message(O+"  * "+W+"Upgrade script returned unexpected code: "+str(returncode), 2)
					self.exit_gracefully(1)

				self.message(O+"  * "+W+"Successfully updated! Please relaunch pacvert.")
				self.exit_gracefully()

			else:
				self.message(O+"  * "+W+"Pacvert Version:\tUp to date")
		except IOError:
			self.message("Unknown error occured while updating.", 2)
			self.exit_gracefully(1)

	def handle_args(self):
		"""
			Handles command line inputs
		"""
		opt_parser = self.build_opt_parser()
		options = opt_parser.parse_args()
		try:
			if options.forcedts:
				self.FORCEDTS=True
			if options.forcex265:
				self.FORCEX265=True
			if options.outdir:
				if os.path.exists(options.outdir):
					self.OUTDIR=options.outdir
				else:
					self.message("Output directory does not exist.",2)
					self.exit_gracefully(1)
		except IndexError:
			self.message("Argument IndexError",2)
			self.exit_gracefully(1)

	def build_opt_parser(self):
		"""
			Options are doubled for backwards compatability; will be removed soon
			and fully moved to GNU-style
		"""
		option_parser = argparse.ArgumentParser()
		command_group = option_parser.add_argument_group('COMMAND')
		command_group.add_argument('--forcedts',help='Force use of dts-codec',action='store_true',dest='forcedts')
		command_group.add_argument('--forcex265',help='Force use of x265-encoder',action='store_true',dest='forcex265')
		command_group.add_argument('--outdir',help='Output directory',action='store',dest='outdir')
		return option_parser

	def banner(self):
		"""
			Display ASCII art
		"""
		global VERSION
		print ("")
		print (C+"      :;;;;;;;;;:    ")
		print (C+"    :;;;;;;;;;;;;:   ")
		print (C+"   ;;;;;;;;;;;;;;::  ")
		print (C+"   ;;;;;;;;;;;;;;;;; ")
		print (C+"  ;;;;;;``;;;; ;;;;; "+W+"Pacvert v"+str(VERSION))
		print (C+"  ;;;;;` ' ;;  ';;;; ")
		print (C+"  ;;;;;  +,;; :+;;;; "+GR+"Automated video conversion")
		print (C+"  ;;;;;;  ;;;` `;;;; ")
		print (C+"  ;;;;;;;;;;;;;;;;;; "+GR+"Designed for Linux/OSX")
		print (C+"  ;;;;;;;;;;;;;;;;;; ")
		print (C+"  ;;;;;;;;;;;;;;;;;; ")
		print (C+"  ;;;  ;;;; ;;;;`';; ")
		print (C+"  ;;    ;;   ;;`  ;; ")
		print (W)
	
	def exit_gracefully(self,code=0):
		"""
			We may exit the program at any time.
			We want to remove the temp folder and any files contained within it.
		"""
		from shutil import rmtree
		if os.path.exists(self.TEMP):
			rmtree(self.TEMP)
		print (R+" [!]"+W+" quitting.")
		print ("")
		exit(code)
		

Pacvert()
