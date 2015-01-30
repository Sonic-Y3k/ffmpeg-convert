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
import configparser

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
		# Initialize Banner
		self.banner()
	
		self.loadConfigFile()
		print(self.config.getboolean("FileSettings","DeleteFile"))
	
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
		#if os.path.exists(self.TEMP):
		#	rmtree(self.TEMP)
		print (R+" [!]"+W+" quitting.")
		print ("")
		exit(code)
		

Pacvert()
