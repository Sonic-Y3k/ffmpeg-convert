#!/usr/bin/python2

# -*- coding: utf-8 -*-

"""
	Convert with Pacman
	
	author: sonic.y3k at googlemail dot com
	
	Licensed under the GNU General Public License Version 2 (GNU GPL v2),
        available at: http://www.gnu.org/licenses/gpl-2.0.txt
	
	(c) 2014
"""

#############
# LIBRARIES #
#############

import os			# File management
import time			# Measuring attack intervals
import datetime		# Time Conversion
import random		# Generating a random numbers.
import errno		# Error numbers
import fnmatch		# Finding files.
import re			# Regular Expressions
import string		# Remove unicode data
import select
import shlex
import argparse

import fcntl
from progressbar import *

from sys import argv          # Command-line arguments
from sys import stdout, stdin # Flushing

from shutil import copy # Copying files
from shutil import rmtree #Remove temp dir

# Executing, communicating with, killing processes
from subprocess import Popen, call, PIPE, check_output, CalledProcessError
from signal import SIGINT, SIGTERM

import urllib2 # Check for new versions from the repo

################################
# Global Variables in all caps #
################################

VERSION = 2.0;

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

	
# /dev/null, send output from programs so they don't print to screen.
DN = open(os.devnull, 'w')

#List for all files.
TOCONVERT = []

###################
# DATA STRUCTURES #
###################

class StreamInfo:
	"""
		Holds data for a Stream
	"""
	def __init__(self,datalines):
		for a in datalines:
			(key,val)=a.strip().split('=')
			self.__dict__[key]=val
	
	def isAudio(self):
		"""
		Is this stream labelled as an audio stream?
		"""
		val=False
		if self.__dict__['codec_type']:
			if str(self.__dict__['codec_type']) == 'audio':
				val=True
		return val

	def isVideo(self):
		"""
		Is the stream labelled as a video stream.
		"""
		val=False
		if self.__dict__['codec_type']:
			if self.codec_type == 'video':
				val=True
		return val

	def isSubtitle(self):
		"""
		Is the stream labelled as a subtitle stream.
		"""
		val=False
		if self.__dict__['codec_type']:
			if str(self.codec_type)=='subtitle':
				val=True
		return val
	
	def frames(self):
		"""
		Returns the length of a video stream in frames. Returns 0 if not a video stream.
		"""
		f=0
		if self.isVideo() or self.isAudio():
			if self.__dict__['nb_frames']:
				f=int(self.__dict__['nb_frames'])
		return f
		
	def durationSeconds(self):
		"""
		Returns the runtime duration of the video stream as a floating point number of seconds.
		Returns 0.0 if not a video stream.
		"""
		f=0.0
		if self.isVideo() or self.isAudio():
			if self.__dict__['duration']:
				f=float(self.__dict__['duration'])
		return f
		
	def fix_lang(self, lang):
		if lang == "alb": return "sqi"
		if lang == "arm": return "hye"
		if lang == "baq": return "eus"
		if lang == "tib": return "bod"
		if lang == "bur": return "mya"
		if lang == "cze": return "ces"
		if lang == "chi": return "zho"
		if lang == "wel": return "cym"
		if lang == "ger": return "deu"
		if lang == "dut": return "nld"
		if lang == "gre": return "ell"
		if lang == "baq": return "eus"	
		if lang == "per": return "fas"	
		if lang == "fre": return "fra"	
		if lang == "geo": return "kat"	
		if lang == "ice": return "isl"	
		if lang == "mac": return "mkd"	
		if lang == "mao": return "mri"	
		if lang == "may": return "msa"	
		if lang == "bur": return "mya"	
		if lang == "per": return "fas"	
		if lang == "rum": return "ron"	
		if lang == "slo": return "slk"	
		if lang == "tib": return "bod"	
		if lang == "wel": return "cym"	
		if lang == "chi": return "zho"
		if lang == "und": return "eng"
		return lang
		
	def language(self):
		"""
		Returns language tag of stream. e.g. eng
		"""
		lang="und"
		try:
			if self.__dict__['TAG:language']:
				lang=self.__dict__['TAG:language']
			elif self.__dict__['TAG:LANGUAGE']:
				lang=self.__dict__['TAG:LANGUAGE']
		except:
			return "eng"
			
		return self.fix_lang(lang)

	def codec(self):
		"""
		Returns a string representation of the stream codec.
		"""
		codec_name=None
		if self.__dict__['codec_name']:
			codec_name=self.__dict__['codec_name']
		return codec_name
	
	def codecDescription(self):
		"""
		Returns a long representation of the stream codec.
		"""
		codec_d=None
		if self.__dict__['codec_long_name']:
			codec_d=self.__dict__['codec_long_name']
		return codec_d
	
	def codecTag(self):
		"""
		Returns a short representative tag of the stream codec.
		"""
		codec_t=None
		if self.__dict__['codec_tag_string']:
			codec_t=self.__dict__['codec_tag_string']
		return codec_t

class MediaInfo:
	"""
		Holds data for a MediaFile
	"""
	def __init__(self, path, name):
		self.path = path
		self.name = name
		self.streams = []
		self.streammap = ""
		self.streamopt = ""
		self.audCount = 0
		self.subCount = 0
		self.addFiles = []

	def add_stream(self, stream):
		self.streams.append(stream)
		
	def add_streammap(self, map):
		self.streammap += " "+map
		
	def add_streamopt(self, opt):
		self.streamopt += " "+opt
	
	def get_flags(self):
		inp="-i "+self.path
		for i in self.addFiles:
			inp=inp+" -i "+i
		return str("ffmpeg "+inp+self.streammap+self.streamopt)

class RunConfiguration:
	"""
		Configuration
	"""
	def __init__(self):
		#File extensions to look for
		self.SEARCHEXT = [".avi",".flv",".mov",".mp4",".mpeg",".mpg",".ogv",".wmv",".m2ts",".rmvb",".rm",".3gp",".m4a",".3g2",".mj2",".asf",".divx",".vob",".mkv"]

		#Default Values
		self.DEFAULT_CRF=18.0
		self.DEFAULT_FILEFORMAT=""
		self.DEFAULT_OUTPUTDIR="output"
		self.DEFAULT_DELETEFILE=False
		self.DEFAULT_X264PROFILE="high"
		self.DEFAULT_X264LEVEL=4.1 
		self.DEFAULT_X264PRESET="slow"
		self.DEFAULT_X264TUNE="film"
		self.DEFAULT_CROPPING=True
		self.DEFAULT_SHUTDOWN=False
		self.DEFAULT_CHOWN=""
		
		if os.uname()[0].startswith("Darwin"):
			self.DEFAULT_AACLIB="libfaac"
			self.DEFAULT_AC3LIB="ac3"
		elif os.uname()[0].startswith("Linux"):
			self.DEFAULT_AACLIB="aac -strict -2"
			self.DEFAULT_AC3LIB="ac3"
		
	def ConfirmCorrectPlatform(self):
		if not os.uname()[0].startswith("Linux") and not 'Darwin' in os.uname()[0]:
			print O + ' [!]' + R + ' WARNING:' + G + ' pacvert' + W + ' must be run on ' + O + 'linux' + W
			exit()
	
	def ConfirmRunningAsRoot(self):
		if os.getuid() != 0:
			print R + ' [!]' + O + ' ERROR:' + G + ' pacvert' + O + ' must be run as ' + R + 'root' + W +' for shutdown'
			print R + ' [!]' + O + ' login as root (' + W + 'su root' + O + ') or try ' + W + 'sudo ./pacvert.py' + W
			return False
		else:
			return True
	
	def setFormat(self, file):
		if self.DEFAULT_FILEFORMAT == "":
			statinfo = os.stat(file)
			if statinfo.st_size > 5368709120:
				self.DEFAULT_FILEFORMAT="mkv"
			else:
				self.DEFAULT_FILEFORMAT="m4v"
	
	def CreateTempFolder(self):
		"""
			Creates temporary directory
		"""
		from tempfile import mkdtemp
		self.temp = mkdtemp(prefix='pacvert')
		if not self.temp.endswith(os.sep):
			self.temp += os.sep
	
	def exit_gracefully(self,code=0):
		"""
			We may exit the program at any time.
			We want to remove the temp folder and any files contained within it.
			Removes the temp files/folder and exists with error code "code".
		"""
		# Remove temp files and folder
		if os.path.exists(self.temp):
			rmtree(self.temp)

		print (R+" [!]"+W+" quitting")
		print ''
		
		exit(code)
	
	def handle_args(self):
		"""
			Handles command-line arguments, sets global variables.
		"""
		opt_parser = self.build_opt_parser()
		options = opt_parser.parse_args()
		
		try:
			if options.directory:
				print GR + ' [+]' + W + ' changing output directory to: \"' + G + options.directory + W + '\".'
				self.DEFAULT_OUTPUTDIR = options.directory
				
			if options.ext and (options.ext == "m4v" or options.ext == "mkv"):
				print GR + ' [+]' + W + ' changing output file extension to: \"' + G + options.ext + W + '\".'
				self.DEFAULT_FILEFORMAT = options.ext
				
			if options.rmfile:
				print GR + ' [+]' + W + ' deleting original file afterwards.'+ W
				self.DEFAULT_DELETEFILE = True
				
			if options.crf:
				print GR + ' [+]' + W +' changing crf to: \"' + G + str(options.crf) + W + '\".'
				self.DEFAULT_CRF = options.crf
				
			if options.x264profile:
				print GR + ' [+]' + W + ' changing x264-preset to: \"' + G + options.x264preset + W + '\".'
				self.DEFAULT_X264PROFILE = options.x264preset
				
			if options.x264level:
				print GR + ' [+]' + W + ' changing x264-level to: \"' + G + options.x264level + W + '\".'
				self.DEFAULT_X264LEVEL = options.x264level
				
			if options.x264preset:
				print GR + ' [+]' + W + ' changing x264-preset to: \"' + G + options.x264preset + W + '\".'
				self.DEFAULT_X264PRESET = options.x264preset
				
			if options.x264tune:
				print GR + ' [+]' + W + ' changing x264-tune to: \"' + G + options.x264tune + W + '\".'
				self.DEFAULT_X264TUNE = options.x264tune
			
			if not options.nocrop:
				print GR + ' [+]' + W + ' disable cropping'+ W + '.'
				self.DEFAULT_CROPPING=options.nocrop
				
			if options.shutdown:
				if options.shutdown and self.ConfirmRunningAsRoot():
					print GR + ' [+]' + W + ' enabling shutdown'+ W + '.'
					self.DEFAULT_SHUTDOWN=options.shutdown
				else:
					print R + ' [!]' + W + ' shutdown '+ O + 'needs'+ W +' chown flag.'
					self.exit_gracefully(1)
					
			if options.chown:
				from pwd import getpwnam
				try:
					t = getpwnam(options.chown)
				except KeyError:
					print R + ' [!]' + W + ' user '+ O + options.chown + W +' does not exist.'
					self.exit_gracefully(1)
					
				print GR + ' [+]' + W + ' changing user to: \"' + G + options.chown + W + '\".'
				self.DEFAULT_CHOWN=options.chown
		except IndexError:
			print '\nindexerror\n\n'

	def build_opt_parser(self):
		"""
			Options are doubled for backwards compatability; will be removed soon and
			fully moved to GNU-style
		"""
		option_parser = argparse.ArgumentParser()
		# set commands
		command_group = option_parser.add_argument_group('COMMAND')
		command_group.add_argument('--chown', help='Change output user.', action='store', dest='chown')
		command_group.add_argument('--crf', help='Change crf-video value to <float>.', action='store', type=float, dest='crf')
		command_group.add_argument('--ext', help='Change output extension.', action='store', dest='ext', choices=['m4v','mkv'])
		command_group.add_argument('--nocrop', help='Disable cropping', action='store_false', dest='nocrop')
		command_group.add_argument('--outdir', help='Change outdir to <directory>.', action='store', dest='directory')
		command_group.add_argument('--rmfile', help='Remove original video.', action='store_true', dest='rmfile')
		command_group.add_argument('--shutdown', help='Shutdown after finishing all jobs.', action='store_true', dest='shutdown')
		command_group.add_argument('--x264level', help='Change x264-level', action='store', type=float, dest='x264level', choices=['1','1b','1.1','1.2','1.3','2','2.1','2.2','3','3.1','3.2','4','4.1','4.2', '5', '5.1'])
		command_group.add_argument('--x264preset', help='Change x264-preset', action='store', dest='x264preset', choices=['ultrafast','superfast','veryfast','faster','fast','medium','slow','slower','veryslow','placebo'])
		command_group.add_argument('--x264profile', help='Change x264-profile', action='store', dest='x264profile', choices=['baseline','main','high','high10','high422','high444'])
		command_group.add_argument('--x264tune', help='Change x264-tune', action='store', dest='x264tune', choices=['film','animation','grain','stillimage','psnr','ssim','fastdecode','zerolatency'])
		
		return option_parser
        
##################
# MAIN FUNCTIONS #
##################

def help():
	"""
		Prints help screen
	"""
	head = W
	sw = G
	var = GR
	des = W
	de = G
	print head + '   COMMANDS' + W
	print sw + '\t--outdir ' + var + '<directory>\t' + des + 'Change output [directory].' + var + '<file>' + des + ' for convertet files.' + W
	
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

def internet_on():
	"""
		Checks if we have an working internet connection.
	"""
	try:
		response=urllib2.urlopen('http://google.com',timeout=1)
		return True
	except urllib2.URLError as err: pass
	return False

def upgrade(RUN_CONFIG):
	"""
		Checks for new Version, promts to upgrade, then
		replaces this script with the latest from the repo.
	"""
	global VERSION
	try:
		if not internet_on():
			print (GR+" [!]"+W+" upgrading requires an "+R+"internet connection"+W)
		else:
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
					RUN_CONFIG.exit_gracefully(1)

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
					RUN_CONFIG.exit_gracefully(1)

				# Run the script
				returncode = call(['sh','update_pacvert.sh'])
				if returncode != 0:
					print (R+' [!]'+O+' upgrade script returned unexpected code: '+str(returncode)+W)
					RUN_CONFIG.exit_gracefully(1)

				print (GR+' [+] '+G+'updated!'+W+' type "./' + this_file + '" to run again')
			else:
				print (GR+' [-]'+W+' your copy of Pacvert is '+G+'up to date'+W)

	except KeyboardInterrupt:
		print (R+'\n (^C)'+O+' Pacvert upgrade interrupted'+W)
		RUN_CONFIG.exit_gracefully(0)

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

def initial_check(RUN_CONFIG):
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
		RUN_CONFIG.exit_gracefully(1)
		
	if not program_exists("mplayer"):
		print (R+" [!]"+O+" required program not found: mplayer"+W)
		if program_exists("brew"):
			print (R+"    "+O+"   install with "+C+"brew install mplayer"+W)
		else:
			print (R+"    "+O+"   available at "+C+"http://mplayerhq.hu/"+W)
		RUN_CONFIG.exit_gracefully(1)
	
	if not program_exists("mkvextract"):
		print (R+" [!]"+O+" required program not found: mkvextract"+W)
		print (R+"    "+O+"   this tool is part of the mkvtoolnix suite"+W)
		if program_exists("brew"):
			print (R+"    "+O+"   install with "+C+"brew install mkvtoolnix"+W)
		else:
			print (R+"    "+O+"   available at "+C+"http://bunkus.org/videotools/mkvtoolnix/"+W)
		RUN_CONFIG.exit_gracefully(1)
		
	if not program_exists("bdsup2sub"):
		print (R+" [!]"+O+" required program not found: bdsup2sub"+W)
		if program_exists("brew"):
			print (R+"    "+O+"   install with "+C+"brew install https://raw.githubusercontent.com/Sonic-Y3k/homebrew/master/bdsup2sub++.rb"+W)
		else:
			print (R+"    "+O+"   available at "+C+"http://forum.doom9.org/showthread.php?p=1613303"+W)
		RUN_CONFIG.exit_gracefully(1)
	
	if not program_exists("tesseract"):
		print (R+" [!]"+O+" required program not found: tesseract"+W)
		if program_exists("brew"):
			print (R+"    "+O+"   install with "+C+"brew install tesseract --all-languages"+W)
		else:
			print (R+"    "+O+"   available at "+C+"http://code.google.com/p/tesseract-ocr/"+W)
			print (R+"    "+O+"   please install with "+C+"all"+W+" available language packs.")
		RUN_CONFIG.exit_gracefully(1)
	
	if not program_exists("vobsub2srt"):
		print (R+" [!]"+O+" required program not found: vobsub2srt"+W)
		if program_exists("brew"):
			print (R+"    "+O+"   install with "+C+"brew install https://raw.githubusercontent.com/ruediger/VobSub2SRT/master/packaging/vobsub2srt.rb --HEAD vobsub2srt"+W)
		else:
			print (R+"    "+O+"   available at "+C+"https://github.com/ruediger/VobSub2SRT"+W)
		RUN_CONFIG.exit_gracefully(1)

def find_files(RUN_CONFIG):
	"""
		Locate files that need a conversion
	"""
	print (GR+" [+]"+W+" searching for files to convert..."+W)
	for root, dirnames, filenames in os.walk(os.getcwd()):
		for filename in filenames:
			file_ext = os.path.splitext(filename)
			if file_ext[1] in RUN_CONFIG.SEARCHEXT and root != os.getcwd()+"/output":
				TOCONVERT.append(MediaInfo(root+"/"+filename, file_ext[0]))		
	
	filecount = len(TOCONVERT)
	if filecount > 0:
		print (GR+" [-]"+W+" found "+C+str(filecount)+W+" files.")
	else:
		print (R+" [!]"+W+" found "+R+str(filecount)+W+" files.")
		RUN_CONFIG.exit_gracefully(0)
		
def analyze_crop(file):
	"""
		Analyze a given file weather
		we need to crop
	"""
	try:
		a=0
		crop=1
		total_loops=10
		ret = []
		crop = []
		crop_row = []
		
		while a < total_loops:
			a+=1
			skip_secs=35*a
			cmd = [ "mplayer", file, "-ss", str(skip_secs), "-identify", "-frames", "20", "-vo", "md5sum", "-ao", "null", "-nocache", "-quiet", "-vf", "cropdetect=20:16" ]
			proc_mplayer = check_output(cmd, stderr=DN)
			for c in re.sub(r'[^\x00-\x7F]+',' ', proc_mplayer.decode(stdout.encoding)).split('\n'):
				cout = c.split(' ')
				if cout[0] == "[CROP]":
					crop_row.append(cout[10].split("=")[1].split(")")[0].split(":")[0])
					crop_row.append(cout[10].split("=")[1].split(")")[0].split(":")[1])
					crop_row.append(cout[10].split("=")[1].split(")")[0].split(":")[2])
					crop_row.append(cout[10].split("=")[1].split(")")[0].split(":")[3])
					crop.append(crop_row)
					crop_row=[]
			
			os.remove("./md5sums")
		
		crop_row.append(crop[0][0])
		crop_row.append(crop[0][1])
		crop_row.append(crop[0][2])
		crop_row.append(crop[0][3])
		ret=crop_row
		
		crop_row = []
		
		for c in crop:
			if int(c[0]) > int(ret[0]):
				ret[0] = c[0]
				ret[2] = c[2]
				
			if int(c[1]) > int(ret[1]):
				ret[1] = c[1]
				ret[3] = c[3]
	except:
		print (R+" [!]"+W+" there was a problem in the cropping department.")
		RUN_CONFIG.exit_gracefully(1)	
	return ret[0]+":"+ret[1]+":"+ret[2]+":"+ret[3]

def convertSubtitle(path,index,lang,RUN_CONFIG):
	"""
		Converts video subtitles to
		text subtitles
	"""
	try:
		tempPath=RUN_CONFIG.temp+os.path.splitext(os.path.basename(path))[0]+"."+index
		
		
		cmd_mkvextract	= ["mkvextract", "tracks", path, index+":"+tempPath+".sup"]
		cmd_bdsup2sub	= ["bdsup2sub", "-o", tempPath+".sub", tempPath+".sup"]
		cmd_vobsub2srt	= ["vobsub2srt", "--tesseract-lang", lang, tempPath, "--verbose"]
		proc_mkvextract	= Popen(cmd_mkvextract, stdout=PIPE)
		widgets = [GR+" [-]"+W+" extracting subtitle\t", Percentage(), ' ', Bar(marker='#',left='[',right=']'),' ', ETA()] #see docs for other options
		pbar = ProgressBar(widgets=widgets, maxval=100)
		pbar.start()
		prev=0
		while proc_mkvextract.poll() is None:
			if not proc_mkvextract.stdout: break
			out = os.read(proc_mkvextract.stdout.fileno(), 1024)
			if out != "":
				out = int(re.sub("[^0-9]", "", out))
				if out > prev and out >= 0 and out <= 100: 
					pbar.update(out)
					prev=out
				stdout.flush()
		pbar.finish()

		widgets = [GR+" [-]"+W+" extracting frames  \t", Percentage(), ' ', Bar(marker='#',left='[',right=']'),' ', ETA()] #see docs for other options
		pbar = ProgressBar(widgets=widgets, maxval=100)
		pbar.start()
		proc_bdsup2sub	= Popen(cmd_bdsup2sub, stderr=DN, stdout=PIPE)
		prev=0.0
		while proc_bdsup2sub.poll() is None:
			if not proc_bdsup2sub.stdout: break
			out = os.read(proc_bdsup2sub.stdout.fileno(), 1024)
			
			if "Decoding frame" in out:
				out=out.split(" ")
				out=out[2].split("/")
				
				num=round(float(out[0])/float(out[1])*100)
				if num > prev and num >= 0 and num <= 100: 
					pbar.update(num)
					prev=num
		pbar.finish()
		
		widgets = [GR+" [-]"+W+" using ocr on frames\t", Percentage(), ' ', Bar(marker='#',left='[',right=']'),' ', ETA()] #see docs for other options
		length=0
		ins = open(tempPath+'.idx', "r")
		for line in ins:
			if "timestamp" in line:
				length+=1
				
		pbar = ProgressBar(widgets=widgets, maxval=length)
		pbar.start()
		proc_vobsub2srt	= Popen(cmd_vobsub2srt, stderr=DN, stdout=PIPE)
		prev=0
		while proc_vobsub2srt.poll() is None:
			if not proc_vobsub2srt.stdout: break
			out = os.read(proc_vobsub2srt.stdout.fileno(), 1024)
			out = out.split(" ")
			out = out[0]
			if out.isdigit():
				num = int(out)
				
			if num == prev+1 and num >= 0 and num <= length:
						pbar.update(num)
						prev=num
		pbar.finish()
		return tempPath+".srt"
		
	except CalledProcessError, e:
		print e
		RUN_CONFIG.exit_gracefully(1)
	
def analyze_files(RUN_CONFIG):
	"""
		Analyze the files we found for
		cropping and subtitles and add
		conversion flags to object.
	"""
	response = raw_input(GR+" [+]"+W+" do you want to analyze the files (this could take some time)? (y/n): ")
	if not response.lower().startswith("y"):
		print (GR+" [-]"+W+" analyzing "+O+"aborted"+W)
		RUN_CONFIG.exit_gracefully(0)
	
	time_started = time.time()
	for media in TOCONVERT:
		if os.path.isfile(media.path):
			try:
				RUN_CONFIG.setFormat(media.path)
				#We beginn with ffprobe to get Stream info
				cmd = [ "ffprobe", "-show_streams", "-pretty", "-loglevel", "quiet", media.path ]
				proc_ffprobe = check_output(cmd, stderr=DN)
				datalines=[]
				for a in re.sub(r'[^\x00-\x7F]+',' ', proc_ffprobe.decode(stdout.encoding)).split('\n'):
					if re.match('\[STREAM\]',a):
						datalines=[]
					elif re.match('\[\/STREAM\]',a):
						media.add_stream(StreamInfo(datalines))
						datalines=[]
					else:
						datalines.append(a)
				
				#Check if we already have an crf value
				cmd = [ "mediainfo", "--Output='Video;%Encoded_Library_Settings%'", media.path ]
				proc_mediainfo = check_output(cmd, stderr=DN)
				crf = 0.0
			
				for b in re.sub(r'[^\x00-\x7F]+',' ', proc_mediainfo.decode(stdout.encoding)).split(' / '):
					if b.split('=')[0] == "crf":
						crf = float(b.split('=')[1].replace(',','.'))
				
				#Let's add some convert-flags
				for c in media.streams:
					if c.isVideo():
						media.add_streammap("-map 0:"+str(c.index))
						if crf < RUN_CONFIG.DEFAULT_CRF:
							#No Copy, need to check cropping!
							media.add_streamopt("-c:v:0 libx264")
							media.add_streamopt("-profile:v "+RUN_CONFIG.DEFAULT_X264PROFILE)
							media.add_streamopt("-level "+str(RUN_CONFIG.DEFAULT_X264LEVEL))
							media.add_streamopt("-preset "+RUN_CONFIG.DEFAULT_X264PRESET)
							media.add_streamopt("-tune "+RUN_CONFIG.DEFAULT_X264TUNE)
							media.add_streamopt("-crf "+str(RUN_CONFIG.DEFAULT_CRF))
							media.add_streamopt("-metadata:s:v:0 language="+c.language())
							
							if RUN_CONFIG.DEFAULT_CROPPING:
								media.add_streamopt("-filter:v crop="+analyze_crop(media.path))
						else:
							#We can copy the video stream
							media.add_streamopt("-c:v:0 copy -metadata:s:v:0 language="+c.language())
				
				for c in media.streams:
					if c.isAudio():
						if RUN_CONFIG.DEFAULT_FILEFORMAT == "mkv" and (c.codec() == "ac3" or c.codec() == "dca" or c.codec() == "truehd"):
							media.add_streammap("-map 0:"+str(c.index))
							media.add_streamopt("-c:a:"+str(media.audCount)+" copy -metadata:s:a:"+str(media.audCount)+" language="+c.language())
							media.audCount+=1
						elif RUN_CONFIG.DEFAULT_FILEFORMAT == "mkv" and (c.codec() != "ac3" and c.codec() != "dca" and c.codec() != "truehd"):
							media.add_streammap("-map 0:"+str(c.index))
							media.add_streamopt("-c:a:"+str(media.audCount)+" "+RUN_CONFIG.DEFAULT_AC3LIB+" -b:a:"+str(media.audCount)+" 640k -ac:"+str(media.audCount)+" "+max(2,c.channels)+" -metadata:s:a:"+str(media.audCount)+" language="+c.language())
							media.audCount+=1
						elif RUN_CONFIG.DEFAULT_FILEFORMAT == "m4v" and (c.codec() == "ac3" or c.codec() == "aac"):
							doubleLang = 0
							for d in media.streams:
								if d.isAudio() and ((c.codec() == "ac3" and d.codec() == "aac") or (c.codec() == "aac" and d.codec() == "ac3")) and c.language() == d.language():
									doubleLang = 1
							
							if doubleLang == 0 and c.codec() == "ac3":
								media.add_streammap("-map 0:"+str(c.index)+" -map 0:"+str(c.index))
								media.add_streamopt("-c:a:"+str(media.audCount)+" "+RUN_CONFIG.DEFAULT_AACLIB+" -b:a:"+str(media.audCount)+" 320k -ac:"+str(media.audCount+1)+" 2 -metadata:s:a:"+str(media.audCount)+" language="+c.language())
								media.audCount+=1
								media.add_streamopt("-c:a:"+str(media.audCount)+" copy -metadata:s:a:"+str(media.audCount)+" language="+c.language())
								media.audCount+=1
							elif doubleLang == 0 and c.codec() == "aac":
								media.add_streammap("-map 0:"+str(c.index)+" -map 0:"+str(c.index))
								media.add_streamopt("-c:a:"+str(media.audCount)+" copy -metadata:s:a:"+str(media.audCount)+" language="+c.language())
								media.audCount+=1
								media.add_streamopt("-c:a:"+str(media.audCount)+" "+RUN_CONFIG.DEFAULT_AC3LIB+" -b:a:"+str(media.audCount)+" 640k -ac:"+str(media.audCount+1)+" "+max(2,c.channels)+" -metadata:s:a:"+str(media.audCount)+" language="+c.language())
								media.audCount+=1
							else:
								media.add_streammap("-map 0:"+str(c.index))
								media.add_streamopt("-c:a:"+str(media.audCount)+" copy -metadata:s:a:"+str(media.audCount)+" language="+c.language())
								media.audCount+=1								
						else:
							media.add_streammap("-map 0:"+str(c.index)+" -map 0:"+str(c.index))
							media.add_streamopt("-c:a:"+str(media.audCount)+" "+RUN_CONFIG.DEFAULT_AACLIB+" -b:a:"+str(media.audCount)+" 320k -ac:"+str(media.audCount+1)+" 2 -metadata:s:a:"+str(media.audCount)+" language="+c.language())
							media.audCount+=1
							media.add_streamopt("-c:a:"+str(media.audCount)+" "+RUN_CONFIG.DEFAULT_AC3LIB+" -b:a:"+str(media.audCount)+" 640k -ac:"+str(media.audCount+1)+" "+max(2,c.channels)+" -metadata:s:a:"+str(media.audCount)+" language="+c.language())
							media.audCount+=1
				
				for c in media.streams:
					if c.isSubtitle():
						if (RUN_CONFIG.DEFAULT_FILEFORMAT == "mkv" and (c.codec() == "ass" or c.codec() == "srt" or c.codec() == "ssa")) or (RUN_CONFIG.DEFAULT_FILEFORMAT == "m4v" and c.codec() == "mov_text"):
							media.add_streammap("-map 0:"+str(c.index))
							media.add_streamopt("-c:s:"+str(media.subCount)+" copy -metadata:s:s:"+str(media.subCount)+" language="+c.language())
							media.subCount+=1
						elif RUN_CONFIG.DEFAULT_FILEFORMAT == "mkv" and c.codec() == "pgssub":
							#Convert to srt
							print (GR+" [-]"+W+" found "+C+"subtitle"+W+" (file: "+media.name+", index: "+c.index+", lang: "+c.language()+") that need to be "+C+"converted"+W)
							newSub=convertSubtitle(media.path, c.index, c.language(),RUN_CONFIG)
							
							if newSub != "":
								media.addFiles.append(newSub)
								media.add_streammap("-map "+str(len(media.addFiles))+":0")
								
								media.add_streamopt("-c:s:"+str(media.subCount)+" copy -metadata:s:s:"+str(media.subCount)+" language="+c.language())
								media.subCount+=1
								
						elif RUN_CONFIG.DEFAULT_FILEFORMAT == "m4v" and c.codec() == "pgssub":
							#Convert to srt and then to mov_text
							print (GR+" [-]"+W+" found "+C+"subtitle"+W+" (file: "+media.name+", index: "+c.index+", lang: "+c.language()+") that need to be "+C+"converted"+W)
							newSub=convertSubtitle(media.path,c.index, c.language(),RUN_CONFIG)
							
							if newSub != "":
								media.addFiles.append(newSub)
								media.add_streammap("-map "+str(len(media.addFiles))+":0")
								
								media.add_streamopt("-c:s:"+str(media.subCount)+" mov_text -metadata:s:s:"+str(media.subCount)+" language="+c.language())
								media.subCount+=1
						else:
							media.add_streammap("-map 0:"+str(c.index))
							if RUN_CONFIG.DEFAULT_FILEFORMAT == "mkv":
								media.add_streamopt("-c:s:"+str(media.subCount)+" srt -metadata:s:s:"+str(media.subCount)+" language="+c.language())
							else:
								media.add_streamopt("-c:s:"+str(media.subCount)+" mov_text -metadata:s:s:"+str(media.subCount)+" language="+c.language())
							media.subCount+=1
							
			except CalledProcessError, e:
				print (R+" [!]"+W+" something doesn't work with "+O+media.path+W+":"+W)
				print (R+" [!]"+W+" "+str(e))
				TOCONVERT.remove(media)
		else:
			RUN_CONFIG.exit_gracefully(1)
	
	time_ended = time.time()
	time_total = time_ended-time_started
	print (GR+" [-]"+W+" analyzing done. This took us "+str(datetime.timedelta(seconds=time_total))+" "+W)
	
def convert_files(RUN_CONFIG,callback=None):
	"""
		Finally convert all the
		files.
	"""
	time_started = time.time()
	
	for media in TOCONVERT:
		if os.path.isfile(media.path):
			try:
				if not os.path.exists(RUN_CONFIG.DEFAULT_OUTPUTDIR):
					os.makedirs(RUN_CONFIG.DEFAULT_OUTPUTDIR)
					if RUN_CONFIG.DEFAULT_CHOWN != "":
						os.system("sudo chown -R "+RUN_CONFIG.DEFAULT_CHOWN+" "+RUN_CONFIG.DEFAULT_OUTPUTDIR)
				RUN_CONFIG.setFormat(media.path)	

				cmd = media.get_flags().split(" ")
				cmd.append("-y")
				#cmd.append("-t")
				#cmd.append("00:01:00.00")
				cmd.append(RUN_CONFIG.DEFAULT_OUTPUTDIR+"/"+media.name+"."+RUN_CONFIG.DEFAULT_FILEFORMAT)
				widgets = [GR+" [-]"+W+" starting conversion\t",' ',Percentage(), ' ', Bar(marker='#',left='[',right=']'),' ',FormatLabel('0 FPS'),' ', ETA()] #see docs for other options
				cmd_med = ["mediainfo", "--Inform=Video;%FrameCount%", media.path]
				frames = float(check_output(cmd_med))
				
				print media.get_flags()
				
				exit(1)
				pipe = Popen(cmd,stderr=PIPE,close_fds=True)
				fcntl.fcntl(pipe.stderr.fileno(),fcntl.F_SETFL,fcntl.fcntl(pipe.stderr.fileno(), fcntl.F_GETFL) | os.O_NONBLOCK)
							
				prev=0
				pbar = ProgressBar(widgets=widgets, maxval=frames,redirect_stdout=True,redirect_stderr=True)
				pbar.start()
				
				time.sleep(2)
				while pipe.poll() is None:
					readx = select.select([pipe.stderr.fileno()], [], [])[0]
					if readx:
						chunk = pipe.stderr.read()
						if chunk == '':
							break
						m = re.findall(r'\d+',chunk)
						out = m[0]
					
						if out.isdigit():
							num = int(out)
				
						if num > prev and num >= 0 and num <= frames:
							widgets[6] = FormatLabel(m[1]+" FPS")
							pbar.update(num)
							prev=num
				
				pbar.finish()
			except CalledProcessError, e:
				print (R+" [!]"+W+" something doesn't work with "+O+media.path+W+":"+W)
				print (R+" [!]"+W+" "+str(e))
				RUN_CONFIG.exit_gracefully(1)
		try:
			newframes=float(check_output(["mediainfo", "--Inform=Video;%FrameCount%", RUN_CONFIG.DEFAULT_OUTPUTDIR+"/"+media.name+"."+RUN_CONFIG.DEFAULT_FILEFORMAT]))
		except ValueError:
			newframes=0
			
		diff=abs(frames-newframes)
		if RUN_CONFIG.DEFAULT_DELETEFILE and diff <= 10:
			print (O+" [W]"+W+" passed sanity check - deleting file"+W)
			os.remove(media.path)
		elif RUN_CONFIG.DEFAULT_DELETEFILE and diff > 10:
			print (R+" [!]"+W+" failed sanity check - keeping file"+W)
		else:
			print (GR+" [W]"+W+" sanity check disabled - keeping file"+W)
		
		if RUN_CONFIG.DEFAULT_CHOWN != "":
			os.system("sudo chown "+RUN_CONFIG.DEFAULT_CHOWN+" "+RUN_CONFIG.DEFAULT_OUTPUTDIR+"/"+media.name+"."+RUN_CONFIG.DEFAULT_FILEFORMAT)
	time_ended = time.time()
	time_total = time_ended-time_started
	print (GR+" [-]"+W+" converting done. This took us "+str(datetime.timedelta(seconds=time_total))+" "+W)
	print (R+" [-]"+W+" bye bye."+W)



if __name__ == '__main__':
	RUN_CONFIG = RunConfiguration()
	try:
		banner()
		RUN_CONFIG.CreateTempFolder()
		RUN_CONFIG.handle_args()
		RUN_CONFIG.ConfirmCorrectPlatform()
		
		upgrade(RUN_CONFIG)
		initial_check(RUN_CONFIG)
		find_files(RUN_CONFIG)
		analyze_files(RUN_CONFIG)
		convert_files(RUN_CONFIG)
		
		if RUN_CONFIG.DEFAULT_SHUTDOWN and RUN_CONFIG.ConfirmRunningAsRoot():
			os.system('sudo shutdown now')

	except KeyboardInterrupt: print (R+'\n (^C)'+O+' interrupted\n'+W)
	except EOFError:          print (R+'\n (^D)'+O+' interrupted\n'+W)

	RUN_CONFIG.exit_gracefully(0)