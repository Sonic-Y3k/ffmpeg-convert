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

import os			# File management
import time			# Measuring attack intervals
import datetime		# Time Conversion
import random		# Generating a random numbers.
import errno		# Error numbers
import fnmatch		# Finding files.
import re			# Regular Expressions
import string		#Remove unicode data

from sys import argv          # Command-line arguments
from sys import stdout, stdin # Flushing

from shutil import copy # Copying files

# Executing, communicating with, killing processes
from subprocess import Popen, call, PIPE, check_output, CalledProcessError
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

#List for all files.
TOCONVERT = []

#File extensions to look for
SEARCHEXT = [".avi",".flv",".mov",".mp4",".mpeg",".mpg",".ogv",".wmv",".m2ts",".rmvb",".rm",".3gp",".m4a",".3g2",".mj2",".asf",".divx",".vob",".mkv"]

#Default Values
DEFAULT_CRF=18.0

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

	def add_stream(self, stream):
		self.streams.append(stream)
		
	def add_streammap(self, map):
		self.streammap += map
		
	def add_streamopt(self, opt):
		self.streamopt += opt
		
	def get_flags(self):
		return str(self.streammap+" "+self.streamopt)

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

def internet_on():
	"""
		Checks if we have an working internet connection.
	"""
	try:
		response=urllib2.urlopen('http://google.com',timeout=1)
		return True
	except urllib2.URLError as err: pass
	return False

def upgrade():
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

def find_files():
	"""
		Locate files that need a conversion
	"""
	print (GR+" [+]"+W+" searching for files to convert..."+W)
	for root, dirnames, filenames in os.walk(os.getcwd()):
		for filename in filenames:
			file_ext = os.path.splitext(filename)
			if file_ext[1] in SEARCHEXT:
				TOCONVERT.append(MediaInfo(root+"/"+filename, file_ext[0]))		
	
	filecount = len(TOCONVERT)
	if filecount > 0:
		print (GR+" [-]"+W+" found "+C+str(filecount)+W+" files.")
	else:
		print (R+" [!]"+W+" found "+R+str(filecount)+W+" files.")
		exit_gracefully(0)
		
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
		exit_gracefully(1)	
	return ret[0]+":"+ret[1]+":"+ret[2]+":"+ret[3]
	
def analyze_files():
	"""
		Analyze the files we found for
		cropping and subtitles and add
		conversion flags to object.
	"""
	response = raw_input(GR+" [+]"+W+" do you want to analyze the files (this could take some time)? (y/n): ")
	if not response.lower().startswith("y"):
		print (GR+" [-]"+W+" analyzing "+O+"aborted"+W)
		exit_gracefully(0)
	
	time_started = time.time()
	for media in TOCONVERT:
		if os.path.isfile(media.path):
			try:
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
						if crf < DEFAULT_CRF:
							#No Copy, need to check cropping!
							media.add_streamopt("-c:v:0 libx264 -profile:v high -level 4.1 -preset slow -crf "+str(DEFAULT_CRF)+" -tune film -filter:v crop="+analyze_crop(media.path)+" -metadata:s:v:0 language="+c.language())
						else:
							#We can copy the video stream
							media.add_streamopt("-c:v:0 copy -metadata:s:v:0 language="+c.language())
						
						print media.streamopt
			except CalledProcessError, e:
				print (R+" [!]"+W+" something doesn't work with "+O+media.path+W+":"+W)
				print (R+" [!]"+W+" "+str(e))
				TOCONVERT.remove(media)
		else:
			exit_gracefully(1)
	
	time_ended = time.time()
	time_total = time_ended-time_started
	print (GR+" [-]"+W+" analyzing done. This took us "+str(datetime.timedelta(seconds=time_total))+" "+W)
	

def exit_gracefully(code=0):
	"""
		May exit the program at any given time.
	"""
	# Remove temp files and folder
	if os.path.exists(temp):
		for file in os.listdir(temp):
			os.remove(temp + file)
		os.rmdir(temp)
	print (R+" [!]"+W+" quitting") # pacman will now exit"
	print ''
	# GTFO
	exit(code)

if __name__ == '__main__':
	try:
		banner()
		upgrade()
		initial_check()
		find_files()
		analyze_files()

	except KeyboardInterrupt: print (R+'\n (^C)'+O+' interrupted\n'+W)
	except EOFError:          print (R+'\n (^D)'+O+' interrupted\n'+W)

	exit_gracefully(0)