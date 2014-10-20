#!/usr/bin/env python
#coding: utf-8
# -*- coding: utf-8 -*-

"""
    Convert with Pacman

    author: sonic.y3k at googlemail dot com

    Licensed under the GNU General Public License Version 2 (GNU GPL v2),
    available at: http://www.gnu.org/licenses/gpl-2.0.txt

    (c) 2014
"""

################################
# Global Variables in all caps #
################################

# Version
VERSION = 3.6;

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
    from progressbar import *
except ImportError:
    print("Please install progressbar2 first.")
    print("sudo pip install progressbar2")
    exit(1)

DN = open(os.devnull,'w')

###################
# Data Structures #
###################

class ToolConvertError(Exception):
    def __init__(self, message, cmd, output, details=None, pid=0):
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
        super(ToolConvertError, self).__init__(message)
        self.cmd = cmd
        self.output = output
        self.details = details
        self.pid = pid

    def __repr__(self):
        error = self.details if self.details else self.message
        return ('<ToolConvertError error="%s", pid=%s, cmd="%s">' % (error, self.pid, self.cmd))

    def __str__(self):
        return self.__repr__()

class PacConf:
    """
        Configuration
    """

    def __init__(self):
        # File extensions to look for
        self.SEARCHEXT = [".avi",".flv",".mov",".mp4",".mpeg",".mpg",".ogv",".wmv",".m2ts",".rmvb",".rm",".3gp",".m4a",".3g2",".mj2",".asf",".divx",".vob",".mkv"]
        self.create_temp()
        self.confirmCorrectPlatform()
        self.DEFAULT_CHOWN = ""
        self.DEFAULT_CRF = 18.0
        self.DEFAULT_CROPPING = True
        self.DEFAULT_DELETEFILE = False
        self.DEFAULT_FILEFORMAT = ""
        self.DEFAULT_NICE = 15
        self.DEFAULT_OUTPUTDIR = os.getcwd()+"/output"
        self.DEFAULT_SHUTDOWN = False
        self.DEFAULT_VERBOSE = False
        self.DEFAULT_X264LEVEL = 4.1
        self.DEFAULT_X264PRESET = "slow"
        self.DEFAULT_X264PROFILE = "high"
        self.DEFAULT_X264TUNE = "film"
        
        self.TOCONVERT = []

        if os.uname()[0].startswith("Darwin"):
            self.DEFAULT_AACLIB="libfaac"
        elif os.uname()[0].startswith("Linux"):
            self.DEFAULT_AACLIB="aac -strict -2"

        self.DEFAULT_AC3LIB="ac3"
        self.check_dep()
        self.upgrade()
        self.handle_args()


    def confirmCorrectPlatform(self):
        """
            Check if we are on Linux / OSX
        """
        if not os.uname()[0].startswith("Linux") and not "Darwin" in os.uname()[0]:
                print (R+" [!]"+O+" ERROR:" +W+" pacvert must be run on "+O+"linux"+W+" or "+O+"osx"+W)

                self.exit_gracefully(1)
    
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

    def check_dep(self):
        # ffmpeg
        self.DEFAULT_FFMPEG = self.program_exists("ffmpeg")
        if self.DEFAULT_FFMPEG:
            print (GR+" [+]"+O+" ffmpeg"+W+":\t\t"+str(self.DEFAULT_FFMPEG))
        else:
            print (R+" [!]"+O+" required program not found: "+C+"ffmpeg"+W)
            self.exit_gracefully(1)
        
        # ffprobe
        self.DEFAULT_FFPROBE = self.program_exists("ffprobe")
        if self.DEFAULT_FFPROBE:
            print (GR+" [+]"+O+" ffprobe"+W+":\t\t"+str(self.DEFAULT_FFPROBE))
        else:
            print (R+" [!]"+O+" required program not found: "+C+"ffprobe"+W)
            self.exit_gracefully(1)

        # mplayer
        self.DEFAULT_MPLAYER = self.program_exists("mplayer")
        if self.DEFAULT_MPLAYER:
            print (GR+" [+]"+O+" mplayer"+W+":\t\t"+str(self.DEFAULT_MPLAYER))
        else:
            print (R+" [!]"+O+" required program not found: "+C+"mplayer"+W)
            self.exit_gracefully(1)

        # mkvextract
        self.DEFAULT_MKVEXTRACT = self.program_exists("mkvextract")
        if self.DEFAULT_MKVEXTRACT:
            print (GR+" [+]"+O+" mkvextract"+W+":\t"+str(self.DEFAULT_MKVEXTRACT))
        else:
            print (R+" [!]"+O+" required program not found: "+C+"mkvextract"+W)
            self.exit_gracefully(1)
        
        # mediainfo
        self.DEFAULT_MEDIAINFO = self.program_exists("mediainfo")
        if self.DEFAULT_MEDIAINFO:
            print (GR+" [+]"+O+" mediainfo"+W+":\t\t"+str(self.DEFAULT_MEDIAINFO))
        else:
            print (R+" [!]"+O+" required program not found: "+C+"mediainfo"+W)
            self.exit_gracefully(1)

        # bdsup2subpp
        self.DEFAULT_BDSUP2SUBPP = self.program_exists("bdsup2subpp")
        if self.DEFAULT_BDSUP2SUBPP:
            print (GR+" [+]"+O+" bdsup2subpp"+W+":\t"+str(self.DEFAULT_BDSUP2SUBPP))
        else:
            print (R+" [!]"+O+" required program not found: "+C+"bdsup2subpp"+W)
            self.exit_gracefully(1)

        # tesseract
        self.DEFAULT_TESSERACT = self.program_exists("tesseract")
        if self.DEFAULT_TESSERACT:
            print (GR+" [+]"+O+" tesseract"+W+":\t\t"+str(self.DEFAULT_TESSERACT))
        else:
            print (R+" [!]"+O+" required program not found: "+C+"tesseract"+W)
            self.exit_gracefully(1)

        # vobsub2srt
        self.DEFAULT_VOBSUB2SRT = self.program_exists("vobsub2srt")
        if self.DEFAULT_VOBSUB2SRT:
            print (GR+" [+]"+O+" vobsub2srt"+W+":\t"+str(self.DEFAULT_VOBSUB2SRT))
        else:
            print (R+" [!]"+O+" required program not found: "+C+"vobsub2srt"+W)
            self.exit_gracefully(1)

    def get_remote_version(self):
        """
        Get's the remote Version from Github
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
                print (R+" [!] invalid version number: '"+page+"'")
        return rver

    def upgrade(self):
        """
        checks for new version
        and upgrades if necessary
        """
        global VERSION
        try:
            remote_version = self.get_remote_version()
            if remote_version == -1:
                print (R+" [!]"+O+" unable to access github"+W)
            elif remote_version > float (VERSION):
                print (GR+" [!]"+W+" version "+G+str(remote_version)+W+" is "+G+"available!"+W)
                try:
                    response = raw_input(GR+" [+]"+W+" do you want to upgrade to the latest version? (y/n): ")
                except NameError:
                    response = input(GR+" [+]"+W+" do you want to upgrade to the latest version? (y/n): ")
                if not response.lower().startswith("y"):
                    print (GR+" [-]"+W+" upgrading "+O+"aborted"+W)
                    return

                print (GR+" [+] "+G+"downloading"+W+" update...")
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
                    print (R+' [+] '+O+'unable to download latest version'+W)
                    self.exit_gracefully(1)

                this_file = __file__
                if this_file.startswith('./'):
                    this_file = this_file[2:]

                f = open('update_pacvert.sh','w')
                f.write('''#!/bin/sh\n
                    rm -rf ''' + this_file + '''\n
                    mv pacvert_new.py ''' + this_file + '''\n
                    rm -rf update_pacvert.sh\n
                    chmod +x ''' + this_file + '''\n
                    ''')
                f.close()

                returncode = call(['chmod','+x','update_pacvert.sh'])
                if returncode != 0:
                    print (R+' [!]'+O+' permission change returned unexpected code: '+str(returncode)+W)
                    self.exit_gracefully(1)

                returncode = call(['sh','update_pacvert.sh'])
                if returncode != 0:
                    print (R+' [!]'+O+' upgrade script returned unexpected code: '+str(returncode)+W)
                    self.exit_gracefully(1)

                print (GR+' [+] '+G+'updated!'+W+' type "' + this_file + '" to run again')
                self.exit_gracefully(0)
            else:
                print (GR+' [-]'+W+' your copy of Pacvert is '+G+'up to date'+W)
        except IOError:
            print (R+' [!]'+W+' something went wront.')
            self.exit_gracefully(1)

    def handle_args(self):
        """
        Handles command line inputs
        """
        opt_parser = self.build_opt_parser()
        options = opt_parser.parse_args()
        try:
            if options.directory:
                print (GR+' [+]'+W+' changing output directory to: \"'+G+options.directory+W+'\".'+W)
                self.DEFAULT_OUTPUTDIR = options.directory
            if options.ext and (options.ext == "m4v" or options.ext == "mkv"):
                print (GR+' [+]'+W+'changing output file extension to: \"'+G+options.ext+W+'\".'+W)
                self.DEFAULT_FILEFORMAT = options.ext
            if options.rmfile:
                print (GR+' [+]'+R+' deleting '+W+'original file afterwards.'+W)
                self.DEFAULT_DELETEFILE = True
            if options.crf:
                print (GR+' [+]'+W+' changing crf to: \"'+G+str(options.crf)+W+'\".'+W)
                self.DEFAULT_CRF = options.crf
            if options.x264profile:
                print (GR+' [+]'+W+' changing x264-preset to: \"'+G+options.x264preset+W+'\".'+W)
                self.DEFAULT_X264PROFILE = options.x264preset
            if options.x264level:
                print (GR+' [+]'+W+' changing x264-level to: \"'+G+options.x264level+W+'\".'+W)
                self.DEFAULT_X264LEVEL = options.x264level
            if options.x264preset:
                print (GR+' [+]'+W+' changing x264-preset to: \"'+G+options.x264preset+W+'\".'+W)
                self.DEFAULT_X264PRESET = options.x264preset
            if options.x264tune:
                print (GR+' [+]'+W+' changing x264-tune to: \"'+G+options.x264tune+W+'\".'+W)
                self.DEFAULT_X264TUNE = options.x264tune
            if not options.nocrop:
                print (GR+' [+]'+W+' disable cropping'+W+'.'+W)
                self.DEFAULT_CROPPING=options.nocrop
            if options.verbose:
                print (GR+' [+]'+W+' enabling verbose mode'+W+'.'+W)
                self.DEFAULT_VERBOSE=True
            if options.nice:
                print (GR+' [+]'+W+' changing nice to: \"'+G+options.nice+W+'\".'+W)
                self.DEFAULT_NICE = options.nice
        except IndexError:
            print ('\nindexerror\n\n')

    def build_opt_parser(self):
        """
        Options are doubled for backwards compatability; will be removed soon
        and fully moved to GNU-style
        """
        option_parser = argparse.ArgumentParser()
        command_group = option_parser.add_argument_group('COMMAND')
        command_group.add_argument('--crf', help='Change crf-video value to <float>.', action='store', type=float, dest='crf')
        command_group.add_argument('--ext', help='Change output extension.', action='store', dest='ext', choices=['m4v','mkv'])
        command_group.add_argument('--nice', help='Change nice value.', action='store', dest='nice', type=int)
        command_group.add_argument('--nocrop', help='Disable cropping', action='store_false', dest='nocrop')
        command_group.add_argument('--outdir', help='Change outdir to <directory>.', action='store', dest='directory')
        command_group.add_argument('--rmfile', help='Remove original video.', action='store_true', dest='rmfile')
        command_group.add_argument('--verbose', help='Enable verbose mode.', action='store_true', dest='verbose')
        command_group.add_argument('--x264level', help='Change x264-level',action='store', type=float, dest='x264level',choices=['1','1b','1.1','1.2','1.3','2','2.1','2.2','3','3.1','3.2','4','4.1','4.2','5', '5.1'])
        command_group.add_argument('--x264preset', help='Change x264-preset',action='store', dest='x264preset',choices=['ultrafast','superfast','veryfast','faster','fast','medium','slow','slower','veryslow','placebo'])
        command_group.add_argument('--x264profile', help='Change x264-profile',action='store', dest='x264profile',choices=['baseline','main','high','high10','high422','high444'])
        command_group.add_argument('--x264tune', help='Change x264-tune',action='store', dest='x264tune',choices=['film','animation','grain','stillimage','psnr','ssim','fastdecode','zerolatency'])
        return option_parser


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
class PacMediaFormatInfo(object):
    """
    Describes the media container format. The attributes are:
      * format - format (short) name (eg. "ogg")
      * fullname - format full (descriptive) name
      * bitrate - total bitrate (bps)
      * duration - media duration in seconds
      * filesize - file size
    """

    def __init__(self):
        self.format = None
        self.fullname = None
        self.bitrate = None
        self.duration = None
        self.filesize = None

    def parse_ffprobe(self, key, val):
        """
        Parse raw ffprobe output (key=value).
        """
        if key == 'format_name':
            self.format = val
        elif key == 'format_long_name':
            self.fullname = val
        elif key == 'bit_rate':
            self.bitrate = PacMediaStreamInfo.parse_float(val, None)
        elif key == 'duration':
            self.duration = PacMediaStreamInfo.parse_float(val, None)
        elif key == 'size':
            self.size = PacMediaStreamInfo.parse_float(val, None)

    def __repr__(self):
        if self.duration is None:
            return 'PacMediaFormatInfo(format=%s)' % self.format
        return 'PacMediaFormatInfo(format=%s, duration=%.2f)' % (self.format,self.duration)

class PacMediaStreamInfo(object):
    """
    Describes one stream inside a media file. The general
    attributes are:
      * index - stream index inside the container (0-based)
      * type - stream type, either 'audio' or 'video'
      * codec - codec (short) name (e.g "vorbis", "theora")
      * codec_desc - codec full (descriptive) name
      * duration - stream duration in seconds
      * metadata - optional metadata associated with a video or audio stream
      * bitrate - stream bitrate in bytes/second
      * attached_pic - (0, 1 or None) is stream a poster image? (e.g. in mp3)
    Video-specific attributes are:
      * video_width - width of video in pixels
      * video_height - height of video in pixels
      * video_fps - average frames per second
    Audio-specific attributes are:
      * audio_channels - the number of channels in the stream
      * audio_samplerate - sample rate (Hz)
    """

    def __init__(self):
        self.index = None
        self.type = None
        self.codec = None
        self.codec_desc = None
        self.duration = None
        self.language = "eng"
        self.bitrate = None
        self.video_width = None
        self.video_height = None
        self.video_fps = None
        self.audio_channels = None
        self.audio_samplerate = None
        self.attached_pic = None
        self.sub_forced = None
        self.sub_default = None
        self.metadata = {}

    @staticmethod
    def parse_float(val, default=0.0):
        try:
            return float(val)
        except:
            return default

    @staticmethod
    def parse_int(val, default=0):
        try:
            return int(val)
        except:
            return default

    def parse_ffprobe(self, key, val):
        """
        Parse raw ffprobe output (key=value).
        """

        if key == 'index':
            self.index = self.parse_int(val)
        elif key == 'codec_type':
            self.type = val
        elif key == 'codec_name':
            self.codec = val
        elif key == 'codec_long_name':
            self.codec_desc = val
        elif key == 'duration':
            self.duration = self.parse_float(val)
        elif key == 'bit_rate':
            self.bitrate = self.parse_int(val, None)
        elif key == 'width':
            self.video_width = self.parse_int(val)
        elif key == 'height':
            self.video_height = self.parse_int(val)
        elif key == 'channels':
            self.audio_channels = self.parse_int(val)
        elif key == 'sample_rate':
            self.audio_samplerate = self.parse_float(val)
        elif key == 'DISPOSITION:attached_pic':
            self.attached_pic = self.parse_int(val)

        if key.startswith('TAG:'):
            key = key.split('TAG:')[1]
            value = val
            if key.lower() == "language":
                self.language = self.fix_lang(val)
                self.metadata[key] = self.fix_lang(val)
            else:
                self.metadata[key] = value

        if self.type == 'audio':
            if key == 'avg_frame_rate':
                if '/' in val:
                    n, d = val.split('/')
                    n = self.parse_float(n)
                    d = self.parse_float(d)
                    if n > 0.0 and d > 0.0:
                        self.video_fps = float(n) / float(d)
                elif '.' in val:
                    self.video_fps = self.parse_float(val)

        if self.type == 'video':
            if key == 'r_frame_rate':
                if '/' in val:
                    n, d = val.split('/')
                    n = self.parse_float(n)
                    d = self.parse_float(d)
                    if n > 0.0 and d > 0.0:
                        self.video_fps = float(n) / float(d)
                elif '.' in val:
                    self.video_fps = self.parse_float(val)

        if self.type == 'subtitle':
            if key == 'disposition:forced':
                self.sub_forced = self.parse_int(val)
            if key == 'disposition:default':
                self.sub_default = self.parse_int(val)

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

    def __repr__(self):
        d = ''
        metadata_str = ['%s=%s' % (key, value) for key, value in self.metadata.items()]
        metadata_str = ', '.join(metadata_str)

        if self.type == 'audio':
            d = 'type=%s, codec=%s, channels=%d, rate=%.0f' % (self.type,self.codec,self.audio_channels,self.audio_samplerate)
        elif self.type == 'video':
            d = 'type=%s, codec=%s, width=%d, height=%d, fps=%.1f' % (self.type,self.codec,self.video_width,self.video_height,self.video_fps)
        elif self.type == 'subtitle':
            d = 'type=%s, codec=%s' % (self.type, self.codec)

        if self.bitrate is not None:
            d += ', bitrate=%d' % self.bitrate

        if self.metadata:
            value = 'MediaStreamInfo(%s, %s)' % (d, metadata_str)
        else:
            value = 'MediaStreamInfo(%s)' % d
        return value

class PacMedia:
    """
        Holds data for a Media and perfoms actions
    """
    def __init__(self,PacConf,path,name):
        self.path = path
        self.name = name
        self.format = PacMediaFormatInfo()
        self.frames = 0
        self.streams = []
        self.streammap = ""
        self.streamopt = ""
        self.audCount = 0
        self.subCount = 0
        self.addFiles = []
        self.PacConf = PacConf
        self.ext = self.PacConf.DEFAULT_FILEFORMAT

    def __repr__(self):
        return 'MediaInfo(format=%s, streams=%s)' % (repr(self.format),repr(self.streams))

    def add_streammap(self,smap):
        self.streammap += " "+smap

    def add_streamopt(self,sopt):
        self.streamopt += " "+sopt

    def getFormat(self):
        if self.ext == "":
            if self.format.size > 5368709120:
                self.ext = "mkv"
            else:
                self.ext = "m4v"
        else:
            self.ext = self.PacConf.DEFAULT_FILEFORMAT

    def getFlags(self):
        cmd = []
        cmd.append(self.PacConf.DEFAULT_FFMPEG)
        cmd.append("-i")
        cmd.append(self.path)
        for i in self.addFiles:
            cmd.append("-i")
            cmd.append(i)
        cmd.extend(self.streammap.split(" "))
        cmd.extend(self.streamopt.split(" "))

        while True:
            try:
                cmd.remove("")
            except ValueError:
                break
        return cmd

    def analyze(self):
        """
            use ffprobe to add all streams to this object.
        """
        if self.PacConf.DEFAULT_VERBOSE:
           print (G+" [V]"+W+" adding streams from ffprobe."+W)

        cmd = [self.PacConf.DEFAULT_FFPROBE,'-show_format','-show_streams',self.path]
        proc_ffprobe = Popen(cmd, shell=False,stdin=PIPE,stdout=PIPE,stderr=PIPE,close_fds=True)

        stdout_data, _ = proc_ffprobe.communicate()
        proc_ffprobe = stdout_data.decode("UTF-8")

        in_format = False
        current_stream = None

        for line in str(proc_ffprobe).split("\n"):
            line = line.strip()
            if line == "":
                continue
            elif line == '[STREAM]':
                current_stream = PacMediaStreamInfo()
            elif line == '[/STREAM]':
                if current_stream.type:
                    self.streams.append(current_stream)
                current_stream = None
            elif line == '[FORMAT]':
                in_format = True
            elif line == '[/FORMAT]':
                in_format = False
            elif '=' in line:
                k, v = line.split('=', 1)
                k = k.strip()
                v = v.strip()
                if current_stream:
                    current_stream.parse_ffprobe(k, v)
                elif in_format:
                    self.format.parse_ffprobe(k, v)
        self.getFormat()

    def analyze_video(self):
        """
            work out compile options
            for video stream
        """
        if self.PacConf.DEFAULT_VERBOSE:
            print (G+" [V]  "+W+" checking for existing crf."+W)

        cmd = [self.PacConf.DEFAULT_MEDIAINFO,"--Output='Video;%Encoded_Library_Settings%'",self.path]
        proc_mediainfo = check_output(cmd, stderr=DN)
        crf = 0.0
        for b in re.sub(r'[^\x00-\x7F]+',' ',proc_mediainfo.decode(stdout.encoding)).split(' / '):
            if b.split('=')[0] == "crf":
                crf = float(b.split('=')[1].replace(',','.'))
                if self.PacConf.DEFAULT_VERBOSE:
                    print (G+" [V]  "+W+" found crf in file: "+O+str(crf)+W)

        if self.PacConf.DEFAULT_VERBOSE:
            print (G+" [V]  "+W+" setting the new values:"+W)

        for c in self.streams:
            if c.type == "video":
                if c.duration < 1:
                    self.frames = round(self.format.duration*c.video_fps)+1
                else:
                    self.frames = round(c.duration*c.video_fps)+1
                self.add_streammap("-map 0:"+str(c.index))

                if crf < self.PacConf.DEFAULT_CRF:
                    self.add_streamopt("-c:v:0 libx264")
                    self.add_streamopt("-profile:v "+self.PacConf.DEFAULT_X264PROFILE)
                    self.add_streamopt("-level "+str(self.PacConf.DEFAULT_X264LEVEL))
                    self.add_streamopt("-preset "+self.PacConf.DEFAULT_X264PRESET)
                    self.add_streamopt("-tune "+self.PacConf.DEFAULT_X264TUNE)
                    self.add_streamopt("-crf "+str(self.PacConf.DEFAULT_CRF))
                    self.add_streamopt("-metadata:s:v:0 language="+c.language)
                    if self.PacConf.DEFAULT_VERBOSE:
                        print (G+" [V]"+W+"    "+O+"-map 0:"+str(c.index)+W)
                        print (G+" [V]"+W+"    "+O+"-c:v:0 libx264"+W)
                        print (G+" [V]"+W+"    "+O+"-profile:v "+self.PacConf.DEFAULT_X264PROFILE+W)
                        print (G+" [V]"+W+"    "+O+"-level "+str(self.PacConf.DEFAULT_X264LEVEL)+W)
                        print (G+" [V]"+W+"    "+O+"-preset "+self.PacConf.DEFAULT_X264PRESET+W)
                        print (G+" [V]"+W+"    "+O+"-tune "+self.PacConf.DEFAULT_X264TUNE+W)
                        print (G+" [V]"+W+"    "+O+"-crf "+str(self.PacConf.DEFAULT_CRF)+W)
                        print (G+" [V]"+W+"    "+O+"-metadata:s:v:0 language="+c.language+W)
                        
                    if self.PacConf.DEFAULT_CROPPING:
                        crop=self.analyze_crop()
                        self.add_streamopt("-filter:v crop="+crop)
                        if self.PacConf.DEFAULT_VERBOSE:
                            print (G+" [V]"+W+"    "+O+"-filter:v crop="+crop+W)
                else:
                    self.add_streamopt("-c:v:0 copy -metadata:s:v:0 language="+c.language)
                    if self.PacConf.DEFAULT_VERBOSE:
                        print (G+" [V]"+W+"    "+O+"-map 0:"+str(c.index)+W)
                        print (G+" [V]"+W+"    "+O+"-c:v:0 copy -metadata:s:v:0 language="+c.language+W)

    def analyze_crop(self):
        """
           Check for cropping
        """
        a = 0
        crop = 1
        total_loops = 10
        ret = []
        crop = []
        crop_row = []

        while a < total_loops:
            a+=1
            skip_secs=35*a
            cmd = [self.PacConf.DEFAULT_MPLAYER,self.path,"-ss",str(skip_secs),"-identify","-frames","20","-vo","md5sum","-ao","null","-nocache","-quiet", "-vf", "cropdetect=20:16" ]
            proc_mplayer = check_output(cmd, stderr=DN)
            for c in str(proc_mplayer.decode("ISO-8859-1")).split('\n'):
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
        return ret[0]+":"+ret[1]+":"+ret[2]+":"+ret[3]

    def analyze_audio(self):
        """
            Work out compile options
            for audio stream
        """
        for c in self.streams:
            if c.type == "audio":
                if self.ext == "mkv" and \
                        (c.codec == "ac3" or c.codec == "dca" or c.codec == "truehd"):
                    self.add_streammap("-map 0:"+str(c.index))
                    self.add_streamopt("-c:a:"+str(self.audCount)+" copy")
                    self.add_streamopt("-metadata:s:a:"+str(self.audCount)+" language="+c.language)
                    
                    if self.PacConf.DEFAULT_VERBOSE:
                        print (G+" [V]"+O+"    -map 0:"+str(c.index)+W)
                        print (G+" [V]"+O+"    -c:a:"+str(self.audCount)+" copy"+W)
                        print (G+" [V]"+O+"    -metadata:s:a:"+str(self.audCount)+" language="+c.language+W)
                    self.audCount+=1
                    
                elif self.ext == "mkv" and \
                        (c.codec != "ac3" and c.codec != "dca" and c.codec != "truehd"):
                    self.add_streammap("-map 0:"+str(c.index))
                    self.add_streamopt("-c:a:"+str(self.audCount)+" "+self.PacConf.DEFAULT_AC3LIB)
                    self.add_streamopt(" -b:a:"+str(self.audCount)+" 640k")
                    self.add_streamopt("-ac:"+str(self.audCount)+" "+str(max(2,c.audio_channels)))
                    self.add_streamopt("-metadata:s:a:"+str(self.audCount)+" language="+c.language)
                    
                    if self.PacConf.DEFAULT_VERBOSE:
                        print (G+" [V]"+O+"    -map 0:"+str(c.index)+W)
                        print (G+" [V]"+O+"    -c:a:"+str(self.audCount)+" "+self.PacConf.DEFAULT_AC3LIB+W)
                        print (G+" [V]"+O+"    -b:a:"+str(self.audCount)+" 640k"+W)
                        print (G+" [V]"+O+"    -ac:"+str(self.audCount)+" "+str(max(2,c.audio_channels))+W)
                        print (G+" [V]"+O+"    -metadata:s:a:"+str(self.audCount)+" language="+c.language+W)
                    self.audCount+=1
                
                elif self.ext == "m4v" and (c.codec == "ac3" or c.codec == "aac"):
                    doubleLang = 0
                    for d in self.streams:
                        if d.type == "audio" and ((c.codec == "ac3" and d.codec == "aac") \
                                or (c.codec == "aac" and d.codec == "ac3")) and c.language == d.language:
                            doubleLang = 1
                    if doubleLang == 0 and c.codec == "ac3":
                        self.add_streammap("-map 0:"+str(c.index)+" -map 0:"+str(c.index))
                        self.add_streamopt("-c:a:"+str(self.audCount)+" "+self.PacConf.DEFAULT_AACLIB)
                        self.add_streamopt("-b:a:"+str(self.audCount)+" 320k")
                        self.add_streamopt("-ac:"+str(self.audCount+1)+" 2")
                        self.add_streamopt("-metadata:s:a:"+str(self.audCount)+" language="+c.language)
                        if self.PacConf.DEFAULT_VERBOSE:
                            print (G+" [V]"+O+"    -map 0:"+str(c.index)+" -map 0:"+str(c.index)+W)
                            print (G+" [V]"+O+"    -c:a:"+str(self.audCount)+" "+self.PacConf.DEFAULT_AACLIB+W)
                            print (G+" [V]"+O+"    -b:a:"+str(self.audCount)+" 320k"+W)
                            print (G+" [V]"+O+"    -ac:"+str(self.audCount+1)+" 2"+W)
                            print (G+" [V]"+O+"    -metadata:s:a:"+str(self.audCount)+" language="+c.language+W)
                        self.audCount+=1
                        self.add_streamopt("-c:a:"+str(self.audCount)+" copy")
                        self.add_streamopt("-metadata:s:a:"+str(self.audCount)+" language="+c.language)
                        if self.PacConf.DEFAULT_VERBOSE:
                            print (G+" [V]"+O+"    -c:a:"+str(self.audCount)+" copy"+W)
                            print (G+" [V]"+O+"    -metadata:s:a:"+str(self.audCount)+" language="+c.language+W)
                        self.audCount+=1
                    elif doubleLang == 0 and c.codec == "aac":
                        self.add_streammap("-map 0:"+str(c.index)+" -map 0:"+str(c.index))
                        self.add_streamopt("-c:a:"+str(self.audCount)+" copy")
                        self.add_streamopt("-metadata:s:a:"+str(self.audCount)+" language="+c.language)
                        if self.PacConf.DEFAULT_VERBOSE:
                            print (G+" [V]"+O+"    -map 0:"+str(c.index)+" -map 0:"+str(c.index)+W)
                            print (G+" [V]"+O+"    -c:a:"+str(self.audCount)+" copy"+W)
                            print (G+" [V]"+O+"    -metadata:s:a:"+str(self.audCount)+" language="+c.language+W)
                        self.audCount+=1
                        self.add_streamopt("-c:a:"+str(self.audCount)+" "+self.PacConf.DEFAULT_AC3LIB)
                        self.add_streamopt("-b:a:"+str(self.audCount)+" 640k")
                        self.add_streamopt("-ac:"+str(self.audCount+1)+" "+str(max(2,c.audio_channels)))
                        self.add_streamopt("-metadata:s:a:"+str(self.audCount)+" language="+c.language)
                        if self.PacConf.DEFAULT_VERBOSE:
                            print (G+" [V]"+O+"    -c:a:"+str(self.audCount)+" "+self.PacConf.DEFAULT_AC3LIB+W)
                            print (G+" [V]"+O+"    -b:a:"+str(self.audCount)+" 640k"+W)
                            print (G+" [V]"+O+"    -ac:"+str(self.audCount+1)+" "+str(max(2,c.audio_channels))+W)
                            print (G+" [V]"+O+"    -metadata:s:a:"+str(self.audCount)+" language="+c.language+W)
                        self.audCount+=1
                    else:
                        self.add_streammap("-map 0:"+str(c.index))
                        self.add_streamopt("-c:a:"+str(self.audCount)+" copy")
                        self.add_streamopt("-metadata:s:a:"+str(self.audCount)+" language="+c.language)
                        if self.PacConf.DEFAULT_VERBOSE:
                            print (G+" [V]"+O+"    -map 0:"+str(c.index)+W)
                            print (G+" [V]"+O+"    -c:a:"+str(self.audCount)+" copy"+W)
                            print (G+" [V]"+O+"    -metadata:s:a:"+str(self.audCount)+" language="+c.language+W)
                        self.audCount+=1
                else:
                    self.add_streammap("-map 0:"+str(c.index)+" -map 0:"+str(c.index))
                    self.add_streamopt("-c:a:"+str(self.audCount)+" "+self.PacConf.DEFAULT_AACLIB)
                    self.add_streamopt("-b:a:"+str(self.audCount)+" 320k")
                    self.add_streamopt("-ac:"+str(self.audCount+1)+" 2")
                    self.add_streamopt("-metadata:s:a:"+str(self.audCount)+" language="+c.language)
                    if self.PacConf.DEFAULT_VERBOSE:
                        print (G+" [V]"+O+"    -map 0:"+str(c.index)+" -map 0:"+str(c.index)+W)
                        print (G+" [V]"+O+"    -c:a:"+str(self.audCount)+" "+self.PacConf.DEFAULT_AACLIB+W)
                        print (G+" [V]"+O+"    -b:a:"+str(self.audCount)+" 320k"+W)
                        print (G+" [V]"+O+"    -ac:"+str(self.audCount+1)+" 2"+W)
                        print (G+" [V]"+O+"    -metadata:s:a:"+str(self.audCount)+" language="+c.language+W)
                    self.audCount+=1
                    self.add_streamopt("-c:a:"+str(self.audCount)+" "+self.PacConf.DEFAULT_AC3LIB)
                    self.add_streamopt("-b:a:"+str(self.audCount)+" 640k")
                    self.add_streamopt("-ac:"+str(self.audCount+1)+" "+str(max(2,c.audio_channels)))
                    self.add_streamopt("-metadata:s:a:"+str(self.audCount)+" language="+c.language)
                    if self.PacConf.DEFAULT_VERBOSE:
                        print (G+" [V]"+O+"    -c:a:"+str(self.audCount)+" "+self.PacConf.DEFAULT_AC3LIB+W)
                        print (G+" [V]"+O+"    -b:a:"+str(self.audCount)+" 640k"+W)
                        print (G+" [V]"+O+"    -ac:"+str(self.audCount+1)+" "+str(max(2,c.audio_channels))+W)
                        print (G+" [V]"+O+" -metadata:s:a:"+str(self.audCount)+" language="+c.language+W)
                    self.audCount+=1

    def analyze_subtitles(self):
        """
            Work out compilation
            falgs for subtitles
        """
        for c in self.streams:
            if c.type == "subtitle":
                if (self.ext == "mkv" and (c.codec == "ass" or c.codec == "srt" or \
                        c.codec == "ssa")) or (self.ext == "m4v" and c.codec == "mov_text"):
                    self.add_streammap("-map 0:"+str(c.index))
                    self.add_streamopt("-c:s:"+str(self.subCount)+" copy")
                    self.add_streamopt("-metadata:s:s:"+str(self.subCount)+" language="+c.language)
                    self.subCount+=1
                elif self.ext == "mkv" and \
                        (c.codec == "pgssub" or c.codec == "dvbsub"):
                    #Convert to srt
                    print (GR+" [-]"+W+" found "+O+"subtitle"+W+" (file: "+self.name+", index: "+str(c.index)+", lang: "+c.language+") that needs to be "+O+"converted"+W)
                    newSub=self.convert_subtitle(c.index,c.language,c.codec)
                    if newSub != "":
                        self.addFiles.append(newSub)
                        self.add_streammap("-map "+str(len(self.addFiles))+":0")
                        self.add_streamopt("-c:s:"+str(self.subCount)+" copy")
                        self.add_streamopt("-metadata:s:s:"+str(self.subCount)+" language="+c.language)
                        self.subCount+=1
                        if self.PacConf.DEFAULT_VERBOSE:
                            print (G+" [V]"+O+"    -map "+str(len(self.addFiles))+":0"+W)
                            print (G+" [V]"+O+"    -c:s:"+str(self.subCount-1)+" copy"+W)
                            print (G+" [V]"+O+"    -metadata:s:s:"+str(self.subCount-1)+" language="+c.language+W)
                elif self.ext == "m4v" and \
                        (c.codec == "pgssub" or c.codec == "dvdsub"):
                    #Convert to srt and then to mov_text
                    print (GR+" [-]"+W+" found "+O+"subtitle"+W+" (file: "+self.name+", index: "+str(c.index)+", lang: "+c.language+") that needs to be "+O+"converted"+W)
                    newSub=self.convert_subtitle(c.index,c.language,c.codec)
                    if newSub != "":
                        self.addFiles.append(newSub)
                        self.add_streammap("-map "+str(len(self.addFiles))+":0")
                        self.add_streamopt("-c:s:"+str(self.subCount)+" mov_text")
                        self.add_streamopt("-metadata:s:s:"+str(self.subCount)+" language="+c.language)
                        self.subCount+=1
                        if self.PacConf.DEFAULT_VERBOSE:
                            print (G+" [V]"+O+"    -map "+str(len(self.addFiles))+":0"+W)
                            print (G+" [V]"+O+"    -c:s:"+str(self.subCount-1)+" copy"+W)
                            print (G+" [V]"+O+"    -metadata:s:s:"+str(self.subCount-1)+" language="+c.language+W)
                else:
                    self.add_streammap("-map 0:"+str(c.index))
                    if self.ext == "mkv":
                        self.add_streamopt("-c:s:"+str(self.subCount)+" srt")
                        self.add_streamopt("-metadata:s:s:"+str(self.subCount)+" language="+c.language)
                        self.subCount+=1
                        if self.PacConf.DEFAULT_VERBOSE:
                            print (G+" [V]"+O+"    -map 0:"+str(c.index)+W)
                            print (G+" [V]"+O+"    -c:s:"+str(self.subCount-1)+" srt"+W)
                            print (G+" [V]"+O+"    -metadata:s:s:"+str(self.subCount-1)+" language="+c.language+W)
                    else:
                        self.add_streamopt("-c:s:"+str(self.subCount)+" mov_text")
                        self.add_streamopt("-metadata:s:s:"+str(self.subCount)+" language="+c.language)
                        self.subCount+=1
                        if self.PacConf.DEFAULT_VERBOSE:
                            print (G+" [V]"+O+"    -map 0:"+str(c.index)+W)
                            print (G+" [V]"+O+"    -c:s:"+str(self.subCount-1)+" mov_text"+W)
                            print (G+" [V]"+O+"    -metadata:s:s:"+str(self.subCount-1)+" language="+c.language+W)

    def convert_subtitle_step1(self,cmds,timeout=10):
        """
            Extracts a subtitle from
            source file.
        """
        if timeout:
            def on_sigalrm(*_):
                signal.signal(signal.SIGALRM,signal.SIG_DFL)
                raise Exception("timed out while waiting for mkvextract")
            signal.signal(signal.SIGALRM,on_sigalrm)

        try:
            p = Popen(cmds,shell=False,stdin=PIPE,stdout=PIPE,stderr=PIPE,close_fds=True)
        except OSError:
            raise Exception("Error while calling mkvextract binary")

        yielded = False
        buf = ""
        total_output = ""
        pat = re.compile(r'[A-Za-z]*: ([0-9]*)')

        while True:
            if timeout:
                signal.alarm(timeout)

            ret = p.stdout.read(10)

            if timeout:
                signal.alarm(0)

            if not ret:
                break

            ret = ret.decode("ISO-8859-1")
            total_output += ret
            buf += ret

            if "\r" in buf:
                line,buf = buf.split("\r", 1)
                tmp = pat.findall(line)

                if len(tmp) == 1:
                    yielded = True
                    yield tmp[0]
        if timeout:
            signal.signal(signal.SIGALRM,signal.SIG_DFL)

        p.communicate()

        if total_output == "":
            raise Exception("Error while calling mkvextract binary")
        
        cmd = " ".join(cmds)
        if "\n" in total_output:
            line = total_output.split("\n")[-2]
            if line.startswith("Received signal"):
                raise ToolConvertError(line.split(':')[0], cmd, total_output,pid=p.pid)
            if not yielded:
                 raise ToolConvertError('Unknown mkvextract error', cmd,total_output, line, pid=p.pid)
        if p.returncode != 0:
            raise ToolConvertError('Exited with code %d' % p.returncode,cmd,total_output, pid=p.pid)

    def convert_subtitle_step2(self,cmds,timeout=10):
        """
            Extracts a subtitle from
            source file.
        """
        if timeout:
            def on_sigalrm(*_):
                signal.signal(signal.SIGALRM,signal.SIG_DFL)
                raise Exception("timed out while waiting for bdsup2subpp")
            signal.signal(signal.SIGALRM,on_sigalrm)

        try:
            p = Popen(cmds,shell=False,stdin=PIPE,stdout=PIPE,stderr=PIPE,close_fds=True)
        except OSError:
            raise Exception("Error while calling bdsup2subpp binary")

        yielded = False
        buf = ""
        total_output = ""
        pat = re.compile(r'[A-Za-z ]*([0-9]*)\/([0-9]*)')

        while True:
            if timeout:
                signal.alarm(timeout)

            ret = p.stdout.read(10)

            if timeout:
                signal.alarm(0)

            if not ret:
                break

            ret = ret.decode("ISO-8859-1")
            total_output += str(ret)
            buf += str(ret)
            if "\n" in buf:
                line,buf = buf.split("\n", 1)
                tmp = pat.findall(line)

                if len(tmp) == 1 and tmp[0][0] is not "" and tmp[0][1] is not "":
                    yielded = True
                    yield tmp[0]
        if timeout:
            signal.signal(signal.SIGALRM,signal.SIG_DFL)

        p.communicate()

        if total_output == "":
            raise Exception("Error while calling bdsup2subpp binary")
        
        cmd = " ".join(cmds)
        if "\n" in total_output:
            line = total_output.split("\n")[-2]
            if line.startswith("Received signal"):
                raise ToolConvertError(line.split(':')[0], cmd, total_output,pid=p.pid)
            if not yielded:
                raise ToolConvertError('Unknown bdsup2subpp error', cmd,total_output, line, pid=p.pid)
        if p.returncode != 0:
            raise ToolConvertError('Exited with code %d' % p.returncode,cmd,total_output, pid=p.pid)

    def convert_subtitle_step3(self,cmds,timeout=10):
        """
            Extracts a subtitle from
            source file.
        """
        if timeout:
            def on_sigalrm(*_):
                signal.signal(signal.SIGALRM,signal.SIG_DFL)
                raise Exception("timed out while waiting for vobsub2srt")
            signal.signal(signal.SIGALRM,on_sigalrm)
        
        try:
            test = Popen([self.PacConf.DEFAULT_TESSERACT, "--list-langs"], stdout=PIPE, stderr=PIPE)
            data = test.communicate()[1].split()
            lang = str(cmds[2])
            if lang not in str(data):
                cmds.remove(lang)
                cmds.remove("--tesseract-lang")

            p = Popen(cmds,shell=False,stdin=PIPE,stdout=PIPE,stderr=PIPE,close_fds=True)
        except OSError:
            raise Exception("Error while calling vobsub2srt binary")

        yielded = False
        buf = ""
        total_output = ""
        pat = re.compile(r'([0-9]*).*')
        
        while True:
            if timeout:
                signal.alarm(timeout)

            ret = p.stdout.readline()
        
            if timeout:
                signal.alarm(0)

            if not ret:
                break

            ret = ret.decode("ISO-8859-1")
            total_output += ret
            buf += ret

            tmp = pat.findall(ret)
            if tmp[0] is not "" and tmp[0].isdigit():
                yielded = True
                yield tmp[0]

        if timeout:
            signal.signal(signal.SIGALRM,signal.SIG_DFL)

        p.communicate()

        if total_output == "":
            raise Exception("Error while calling vobsub2srt binary")
        
        cmd = " ".join(cmds)
        if "\n" in total_output:
            line = total_output.split("\n")[-2]
            if line.startswith("Error opening data file"):
                raise ToolConvertError("Tesseract language not found.", cmd, total_output,pid=p.pid)
            if line.startswith("Received signal"):
                raise ToolConvertError(line.split(':')[0], cmd, total_output,pid=p.pid)
            if not yielded:
                 raise ToolConvertError('Unknown vobsub2srt error', cmd,total_output, line, pid=p.pid)
        if p.returncode != 0:
            raise ToolConvertError('Exited with code %d' % p.returncode,cmd,total_output, pid=p.pid)


    def convert_subtitle(self,index,lang,codec,timeout=10):
        """
            Converts subtitle to srt
        """
        tempFileName=self.PacConf.TEMP+os.path.splitext(os.path.basename(self.path))[0]+"."+str(index)
        if codec != "dvdsub":
            cmd_mkvextract=[self.PacConf.DEFAULT_MKVEXTRACT,"tracks",self.path,str(index)+":"+tempFileName+".sup"]
        else:
            cmd_mkvextract=[self.PacConf.DEFAULT_MKVEXTRACT,"tracks",self.path,str(index)+":"+tempFileName+".sub"]
        cmd_bdsup2subpp=[self.PacConf.DEFAULT_BDSUP2SUBPP,"-o",tempFileName+".sub",tempFileName+".sup"]
        
        if os.path.isdir("/usr/share/tessdata"):
            tessdata = "/usr/share/tessdata"
        else:
            tessdata = "/usr/local/share/tessdata"
        
        cmd_vobsub2srt=[self.PacConf.DEFAULT_VOBSUB2SRT,"--tesseract-lang",lang,"--tesseract-data",tessdata,tempFileName,"--verbose"]
    
        #First Block, let's extract the subtitle from file.
        widgets = [GR+" [-]"+W+" extracting subtitle\t",Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
        pbar = ProgressBar(widgets=widgets, maxval=100)
        pbar.start()
        step1 = self.convert_subtitle_step1(cmd_mkvextract)
        pval = 0
        for val in step1:
            try:
                temp = int (val)
            except TypeError:
                temp = pval

            if temp > pval and temp < 101:
                pbar.update(temp)
                pval = temp
        pbar.finish()
        
        if codec != "dvdsub":
            #Second Block, extract frames from subtitle
            widgets = [GR+" [-]"+W+" extracting frames  \t",Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
            pbar = ProgressBar(widgets=widgets, maxval=100.0)
            pbar.start()
            step2 = self.convert_subtitle_step2(cmd_bdsup2subpp)
            pval = 0.0
            for val in step2:
                try:
                    temp = float(int(val[0])/int(val[1]))*100
                except TypeError:
                    temp = pval

                if temp > pval and temp <= 1:
                    pbar.update(temp)
                    pval = temp
            pbar.finish()
        
        #Third Block, ocr extracted frames
        widgets = [GR+" [-]"+W+" using ocr on frames\t",Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',ETA()]
        length=0
        ins = open(tempFileName+'.idx', "r")
        for line in ins:
            if "timestamp" in line:
                 length+=1
        pbar = ProgressBar(widgets=widgets, maxval=length)
        pbar.start()
        step3 = self.convert_subtitle_step3(cmd_vobsub2srt)
        pval = 0
        for val in step3:
            try:
                temp = int(val)
            except TypeError:
                temp = pval

            if temp > pval and temp <= length:
                pbar.update(temp)
                pval = temp
        pbar.finish()

        if os.path.isfile(tempFileName+".srt"):
            return tempFileName+".srt"
        else:
            return ""

    def convert(self,timeout=10):
        if not os.path.exists(self.path):
            raise Exception("Input file doesn't exists: "+self.path)
        
        if not os.path.exists(self.PacConf.DEFAULT_OUTPUTDIR):
            os.makedirs(self.PacConf.DEFAULT_OUTPUTDIR)


        outfile = self.PacConf.DEFAULT_OUTPUTDIR+"/"+self.name+"."+self.ext
        cmds = self.getFlags()
        cmds.extend(['-y', outfile])

        if timeout:
            def on_sigalrm(*_):
                signal.signal(signal.SIGALRM,signal.SIG_DFL)
                raise Exception("timed out while waiting for ffmpeg")
            signal.signal(signal.SIGALRM,on_sigalrm)

        try:
            p = Popen(cmds,shell=False,stdin=PIPE,stdout=PIPE,stderr=PIPE,close_fds=True)
        except OSError:
            raise Exception("Error while calling ffmpeg binary")
        
        yielded = False
        buf = ""
        total_output = ""
        pat = re.compile(r'frame=\s*([0-9]+)\s*fps=\s*([0-9]+)')
        while True:
            if timeout:
                signal.alarm(timeout)

            ret = p.stderr.read(10)

            if timeout:
                signal.alarm(0)

            if not ret:
                break
            
            ret = ret.decode("ISO-8859-1")
            total_output += ret
            buf += str(ret)
            if "\r" in buf:
                line,buf = buf.split("\r", 1)

                tmp = pat.findall(line)
            
                if len(tmp) == 1:
                    yielded = True
                    yield tmp[0]
        if timeout:
            signal.signal(signal.SIGALRM,signal.SIG_DFL)

        p.communicate()

        if total_output == "":
            raise Exception("Error while calling ffmpeg binary")

        cmd = " ".join(cmds)
        if "\n" in total_output:
            line = total_output.split("\n")[-2]

            if line.startswith("Received signal"):
                raise ToolConvertError(line.split(':')[0], cmd, total_output,pid=p.pid)
            if line.startswith(self.path + ': '):
                err = line[len(self.path) + 2:]
                raise ToolConvertError('Encoding error',cmd,total_output,err,pid=p.pid)
            if line.startswith('Error while '):
                raise ToolConvertError('Encoding error',cmd,total_output,line,pid=p.pid)
            if not yielded:
                raise ToolConvertError('Unknown ffmpeg error', cmd,total_output, line, pid=p.pid)
        if p.returncode != 0:
            raise ToolConvertError('Exited with code %d' % p.returncode,cmd,total_output, pid=p.pid)
            
    def check_sanity(self):
        """
        """
        # Disabling verboseity and cropping to speed up things.
        old_v = self.PacConf.DEFAULT_VERBOSE
        old_c = self.PacConf.DEFAULT_CROPPING
        self.PacConf.DEFAULT_VERBOSE = False
        self.PacConf.DEFAULT_CROPPING = False

        #Analyze output
        output = self.PacConf.DEFAULT_OUTPUTDIR+"/"+self.name+"."+self.ext
        outputf = PacMedia(self.PacConf,output,self.name)
        outputf.analyze()
        outputf.analyze_video()

        # Restore verboseity and cropping
        self.PacConf.DEFAULT_VERBOSE = old_v
        self.PacConf.DEFAULT_CROPPING = old_c

        # Calculate difference in both files
        pre_frames = self.frames
        new_frames = outputf.frames
        diff = int(abs(pre_frames-new_frames))

        #maxdiff in Frames
        maxdiff = 50

        # Proceed...
        if self.PacConf.DEFAULT_DELETEFILE and diff <= maxdiff:
            if self.PacConf.DEFAULT_VERBOSE:
                print (G+" [V]"+W+" passed sanity check - "+O+"deleting"+W+" file"+W)
            os.remove(self.path)
        elif self.PacConf.DEFAULT_DELETEFILE and diff > maxdiff:
            print (R+" [!]"+W+" failed sanity check (max diff: "+str(maxdiff)+" | cur diff: "+str(diff)+") - keeping old & removing new file"+W)
            os.remove(output)
        elif not self.PacConf.DEFAULT_DELETEFILE and diff <= maxdiff:
            if self.PacConf.DEFAULT_VERBOSE:
                print (G+" [V]"+W+" passed sanity check - "+O+"keeping"+W+" file"+W)
        elif not self.PacConf.DEFAULT_VERBOSE and diff > maxdiff:
            print (R+" [!]"+W+" failed sanity check (max diff: "+str(maxdiff)+" | cur diff: "+str(diff)+")  - removing "+O+"NEW"+W+" file"+W)
            os.remove(output)

        #except:
        #    print (R+" [!]"+W+" Something went very [...] very wrong.")
        #    self.PacConf.exit_gracefully(1)

def banner():
    """
        Display ASCII art
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
    print (R+"  ;;;  ;;;; ;;;;`';; ")
    print (R+"  ;;    ;;   ;;`  ;; ")
    print (W)

def searchFiles(PacConf):
    """
        Locate files that need a conversion
    """
    print (GR+" [+]"+W+" searching for files to convert..."+W)
    for root,dirnames,filenames in os.walk(os.getcwd()):
        for filename in filenames:
            file_ext = os.path.splitext(filename)
            if file_ext[1] in PacConf.SEARCHEXT and root != PacConf.DEFAULT_OUTPUTDIR:
                PacConf.TOCONVERT.append(PacMedia(PacConf,root+"/"+filename,file_ext[0]))

if __name__ == '__main__':
    banner()
    try:
        PacConf = PacConf()
        searchFiles(PacConf)
        PacConf.TOCONVERT.sort(key=lambda x: x.name, reverse=False)
        print (GR+" [+]"+W+" ...found "+O+str(len(PacConf.TOCONVERT))+W+" files.")
        currenta = 1
        currentc = 1
        if not PacConf.DEFAULT_VERBOSE:
            widgets = [GR+" [-]"+W+" analyze: "+PacConf.TOCONVERT[0].name[:10]+"... ("+str(currenta).zfill(3)+"/"+str(len(PacConf.TOCONVERT)).zfill(3)+")",' ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ', ETA()] 
            pbar = ProgressBar(widgets=widgets,maxval=len(PacConf.TOCONVERT))
            pbar.start()

        for i in PacConf.TOCONVERT:
            i.analyze()
            i.analyze_video()
            i.analyze_audio()
            i.analyze_subtitles()
            if not PacConf.DEFAULT_VERBOSE:
                widgets[0] = FormatLabel(GR+" [-]"+W+" analyze: "+i.name[:10]+"... ("+str(currenta).zfill(3)+"/"+str(len(PacConf.TOCONVERT)).zfill(3)+")")
                pbar.update(currenta)
            currenta += 1
        if not PacConf.DEFAULT_VERBOSE:
            pbar.finish()

        for i in PacConf.TOCONVERT:            
            conv = i.convert()
            frames = i.frames
            widgets = [GR+" [-]"+W+" convert: "+i.name[:10]+"... ("+str(currentc).zfill(3)+"/"+str(len(PacConf.TOCONVERT)).zfill(3)+")",' ',Percentage(),' ',Bar(marker='#',left='[',right=']'),' ',FormatLabel('0 FPS'),' ', ETA()] 
            pbar = ProgressBar(widgets=widgets,maxval=i.frames)
            pbar.start()
            oltime = time.time()
            pval = 0
            for val in conv:
                try:
                    temp = int(val[0])
                except TypeError:
                    temp = pval
                widgets[6] = FormatLabel(str(val[1])+" FPS")
                if temp <= i.frames:
                    pbar.update(temp)
                    pval = temp
                else:
                    pbar.update(pval)
            pbar.finish()
            i.check_sanity() 
            currentc+=1
    except KeyboardInterrupt: print(R+'\n (^C)'+O+' interrupted\n'+W)
    except EOFError: print (R+'\n (^D)'+O+' interrupted\n'+W)

    PacConf.exit_gracefully()
