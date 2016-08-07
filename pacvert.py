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
VERSION = 4.988;
DATE = "07.08.2016";

# Console colors
W  = '\033[0m'  # white (normal)
R  = '\033[31m' # red
G  = '\033[32m' # green
O  = '\033[33m' # orange
B  = '\033[34m' # blue
P  = '\033[35m' # purple
C  = '\033[36m' # cyan
GR = '\033[37m' # gray

TOCONVERT = []
TOFAIL = []

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
        self.options = {}
        
        #Create temp directory
        self.create_temp()

        #Register strg+c
        signal.signal(signal.SIGINT, self.exit_signal)	

        self.options['threads'] = 0

        # Initialize Banner
        self.banner()

        #Handle CLI Args
        self.handle_args()		
    
        #Check for Unix Systems
        if self.getPlatform() != "Linux" and self.getPlatform() != "Darwin" and self.getPlatform() != 'Cygwin':
            self.message("Only Linux/Darwin is currently supported.",2)
            self.exit_gracefully(1)

        #Load or create config
        self.loadConfigFile()

        #Set to silent
        self.options['silent'] = False

        #Begin dependency check
        self.checkDependencies()

        #misc
        self.message("Miscellaneous Informations:")
        self.message(O+"  * "+W+"Current Directory:\t"+os.getcwd())
        self.message(O+"  * "+W+"Output Directory:\t"+self.options['outdir'])
        self.message(O+"  * "+W+"Temporary Directory:\t"+self.options['temp'])

        #Check for updates
        self.upgrade()
        
        if self.options['nocrop']:
            self.message("["+O+"nocrop"+W+"] Disabling cropping!",1)
        
        #Show message if focing dts
        if self.options['forcedts']:
            self.message("["+O+"forcedts"+W+"] Forcing DTS-Audio!",1)
            self.message("["+O+"forcedts"+W+"] This will be ignored with m4v files.",1)

        #Show message if forcing x265
        if self.options['forcex265']:
            self.message("["+O+"forcex265"+W+"] Forcing x265-Encoder!",1)
            self.message("["+O+"forcex265"+W+"] This is highly experimental!",1)
        
        #Show message if forcing vp9
        if self.options['vp9']:
            self.message("["+O+"vp9"+W+"] Forcing vp9-Encoder!", 1)
            self.message("["+O+"vp9"+W+"] This is highly experimental!")

        #Show message if disabling maxrate
        if self.options['disable_maxrate']:
            self.message("["+O+"disable_maxrate"+W+"] Disabling maxrate.",1)

        #Show message if forcing nooutdir
        if self.options['nooutdir']:
            self.message("["+O+"nooutdir"+W+"] Overwriting source files!",1)
            self.message("["+O+"nooutdir"+W+"] This will ignore --outdir parameter.",1)		
        
        if self.options['snap']:
            self.message("["+O+"snap"+W+"] Only converting first five minutes.",1)

        self.options['config'] = self.config

        #Search for files
        self.searchFiles()
        self.message("Overview:")
        self.message(O+"  * "+W+"Files to convert:\t"+str(len(TOCONVERT)))

        tempbytes = 0
        for a in TOCONVERT:
            tempbytes += a.pacvertFilesize

        self.message(O+"  * "+W+"Cumulative size:\t"+self.sizeof_fmt(tempbytes))

        pbar = ProgressBar(widgets=[G+' [',AnimatedMarker(),'] '+W+'Waiting 15 seconds until analysis starts.\t']).start()
        for i in range(15):
            time.sleep(1)
            pbar.update(i + 1)
        pbar.finish()

        TOCONVERT.sort(key=lambda x: x.pacvertFile, reverse=False)

        #Beginn to convert
        self.message("Converting:")
        currentc = 1
        for element in TOCONVERT:
            #Beginning with deep analysis
            element.analyze(self.tools,self.options)
            element.analyze_video(self.tools,self.options)
            element.analyze_audio(self.tools,self.options)
            element.analyze_subtitles(self.tools,self.options)

            #Default conversion
            current_zero = str(currentc).zfill(len(str(len(TOCONVERT))))
            #calc_len = 1/3 of a window
            calc_len = int(int(os.popen('stty size', 'r').read().split()[1])*0.66) 
            if len(element.pacvertName) > calc_len:
                self.message(O+"  * "+W+element.pacvertName[:(calc_len-3)]+"... ("+current_zero+"/"+str(len(TOCONVERT))+"):")
            else:
                self.message(O+"  * "+W+element.pacvertName+" ("+current_zero+"/"+str(len(TOCONVERT))+"):")
            try:
                conv = element.convert(self.tools,self.options,30)
                frames = element.frames
                leadin_zero = str("0").rjust(len(str(frames)),'0')
                widgets = [G+' [']
                widgets.append(AnimatedMarker())
                widgets.append('] ')
                widgets.append(B+'    + '+W)
                widgets.append(Percentage())
                widgets.append(' (')
                widgets.append(FormatLabel(leadin_zero))
                widgets.append('/'+str(element.frames)+') ')
                widgets.append(Bar(marker='#',left='[',right=']'))
                widgets.append(' ')
                widgets.append(FormatLabel('0 FPS'))
                widgets.append(' ')
                widgets.append(ETA())
            
                pbar = ProgressBar(widgets=widgets,maxval=element.frames)
                pbar.start()
                pval = 0
            
                for val in conv:
                    try:
                        temp = int(val[0])
                    except TypeError:
                        temp = pval
                    
                    widgets[10] = FormatLabel(str(val[1])+" FPS")
                    if temp <= element.frames:
                        pbar.update(temp)
                        pval = temp    
                    else:
                        pbar.update(pval)
                    widgets[6] = FormatLabel(str(pval).rjust(len(str(frames)),'0'))
                pbar.finish()
                currentc += 1
            except PacvertError:
                try:
                    currentc += 1
                    TOFAIL.append(element)
                    pbar.finish()
                except:
                    """"""
            if not self.options['snap']:
                element.check_sanity(self.tools,self.options)

        #Show failed
        if len(TOFAIL) > 0:
            self.message("Failed files:",2)
            self.show_failed()

        #Exit
        self.exit_gracefully()
    
    def show_failed(self):
        result = list(set(TOFAIL))
        for element in result:
            self.message(O+"  * "+W+element.pacvertName,2)
            self.message(B+"    + "+W+"File size:\t"+self.sizeof_fmt(element.pacvertFilesize),2)
            outfile = self.options['outdir']+"/"+os.path.splitext(element.pacvertName)[0]+"."+element.pacvertFileExtensions
            cmds = element.getFlags(self.tools)
            cmds.extend(['-y', outfile])
            cmd = ""
            for c in cmds:
                cmd += " "+c
            self.message(B+"    + "+W+"ffmpeg-cmd:\t\""+cmd+"\"",2)
        
    
    def exit_signal(self,signum,frame):
        self.exit_gracefully(signum)

    def available_cpu_count(self):
        """ Number of available virtual or physical CPUs on this system, i.e.
        user/real as output by time(1) when called with an optimally scaling
        userspace-only program"""

        # cpuset
        # cpuset may restrict the number of *available* processors
        try:
            m = re.search(r'(?m)^Cpus_allowed:\s*(.*)$',open('/proc/self/status').read())
            if m:
                res = bin(int(m.group(1).replace(',', ''), 16)).count('1')
                if res > 0:
                    return res
        except IOError:
            pass

        # Python 2.6+
        try:
            import multiprocessing
            return multiprocessing.cpu_count()
        except (ImportError, NotImplementedError):
            pass

        # http://code.google.com/p/psutil/
        try:
            import psutil
            return psutil.NUM_CPUS
        except (ImportError, AttributeError):
            pass

        # POSIX
        try:
            res = int(os.sysconf('SC_NPROCESSORS_ONLN'))
            if res > 0:
                return res
        except (AttributeError, ValueError):
            pass

        # Windows
        try:
            res = int(os.environ['NUMBER_OF_PROCESSORS'])
            if res > 0:
                return res
        except (KeyError, ValueError):
            pass

        # jython
        try:
            from java.lang import Runtime
            runtime = Runtime.getRuntime()
            res = runtime.availableProcessors()
            if res > 0:
                return res
        except ImportError:
            pass

        # BSD
        try:
            sysctl = subprocess.Popen(['sysctl', '-n', 'hw.ncpu'],stdout=subprocess.PIPE)
            scStdout = sysctl.communicate()[0]
            res = int(scStdout)

            if res > 0:
                return res
        except (OSError, ValueError):
            pass

        # Linux
        try:
            res = open('/proc/cpuinfo').read().count('processor\t:')

            if res > 0:
                    return res
        except IOError:
            pass

        # Solaris
        try:
            pseudoDevices = os.listdir('/devices/pseudo/')
            res = 0
            for pd in pseudoDevices:
                if re.match(r'^cpuid@[0-9]+$', pd):
                    res += 1

            if res > 0:
                return res
        except OSError:
            pass

        # Other UNIXes (heuristic)
        try:
            try:
                dmesg = open('/var/run/dmesg.boot').read()
            except IOError:
                dmesgProcess = subprocess.Popen(['dmesg'], stdout=subprocess.PIPE)
                dmesg = dmesgProcess.communicate()[0]

            res = 0
            while '\ncpu' + str(res) + ':' in dmesg:
                res += 1

            if res > 0:
                return res
        except OSError:
            pass

        raise Exception('Can not determine number of CPUs on this system')

    def searchFiles(self):
        """
            Locate files that need a conversion
        """
        global TOCONVERT
        for root,dirnames,filenames in os.walk(os.getcwd()):
            for filename in filenames:
                file_ext = os.path.splitext(filename)
                if file_ext[1].replace(".","") in self.config.get("FileSettings","SearchExtensions").split(",") and root != self.options['outdir']:
                    #Files appear to be valid, by their extension
                    TOCONVERT.append(PacvertMedia(root+"/"+filename, self.config))
                    
    def create_temp(self):
        """
            Creates temporary directory
        """
        from tempfile import mkdtemp
        self.options['temp'] = mkdtemp(prefix='pacvert')
        if not self.options['temp'].endswith(os.sep):
            self.options['temp'] += os.sep

    def program_exists(self,program):
        """
            Uses "wich" (unix command) to check if a program is installed
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
        try:
            if not self.config:
                """"""
        except AttributeError:
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
                    self.exit_gracefully(1)

                #Recreate configuration file
                self.loadConfigFile()				
        else:
            #Config does not exists... we need to create.
            
            #Set Config Version
            if not self.config.has_section("ConfigVersion"):
                self.config.add_section("ConfigVersion")
            self.config.set("ConfigVersion","Version",str(VERSION))

            #General File Settings
            if not self.config.has_section("FileSettings"):
                self.config.add_section("FileSettings")
            if not self.config.has_option("FileSettings","DeleteFile"):
                self.config.set("FileSettings", "DeleteFile", "True")
            if not self.config.has_option("FileSettings","FileFormat"):
                self.config.set("FileSettings", "FileFormat", "mkv")
            if not self.config.has_option("FileSettings","SearchExtensions"):
                self.config.set("FileSettings", "SearchExtensions", "avi,flv,mov,mp4,mpeg,mpg,ogv,wmv,m2ts,rmvb,rm,3gp,m4v,3g2,mj2,asf,divx,vob,mkv")
            if not self.config.has_option("FileSettings","MaxDiff"):
                self.config.set("FileSettings", "MaxDiff", "50")
            
            #Video Settings
            if not self.config.has_section("VideoSettings"):
                self.config.add_section("VideoSettings")
            if not self.config.has_option("VideoSettings","CRF"):
                self.config.set("VideoSettings","CRF","18.0")
            if not self.config.has_option("VideoSettings","CROP"):
                self.config.set("VideoSettings","CROP", "True")
            if not self.config.has_option("VideoSettings","X264Level"):
                self.config.set("VideoSettings","X264Level","4.1")
            if not self.config.has_option("VideoSettings","X264Preset"):
                self.config.set("VideoSettings","X264Preset","slow")
            if not self.config.has_option("VideoSettings","X264Profile"):
                self.config.set("VideoSettings","X264Profile","high")
            if not self.config.has_option("VideoSettings","X264Tune"):
                self.config.set("VideoSettings","X264Tune","film")
            if not self.config.has_option("VideoSettings","X265Preset"):
                self.config.set("VideoSettings","X265Preset","slow")
            if not self.config.has_option("VideoSettings","X265Tune"):
                self.config.set("VideoSettings","X265Tune","")
            if not self.config.has_option("VideoSettings","X265Params"):
                self.config.set("VideoSettings","X265Params","")
            if not self.config.has_option("VideoSettings","X265CRF"):
                self.config.set("VideoSettings","X265CRF","23.0")
            
            #Audio Settings
            if not self.config.has_section("AudioSettings"):
                self.config.add_section("AudioSettings")
            if not self.config.has_option("AudioSettings","DefaultAudioCodec"):
                self.config.set("AudioSettings","DefaultAudioCodec","")
            if self.getPlatform() == "Linux" or self.getPlatform() == "Cygwin":
                if not self.config.has_option("AudioSettings","AACLib"):
                    self.config.set("AudioSettings","AACLib","aac -strict -2")
            elif self.getPlatform() == "Darwin":
                if not self.config.has_option("AudioSettings","AACLib"):
                    self.config.set("AudioSettings","AACLib","libvo_aacenc")
            if not self.config.has_option("AudioSettings","AC3Lib"):
                self.config.set("AudioSettings","AC3Lib","ac3")
            if not self.config.has_option("AudioSettings","DTSLib"):
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
        if self.getPlatform() == "Linux" or self.getPlatform() == "Cygwin":
            return "/etc/pacvert.conf"
        elif self.getPlatform() == "Darwin":
            return "/usr/local/etc/pacvert.conf"
    
    def getPlatform(self):
        """
            Returns the platform this script is runing on
        """
        if os.uname()[0].startswith("Linux"):
            return "Linux"
        elif "Darwin" in os.uname()[0]:
            return "Darwin"
        elif 'CYGWIN' in os.uname()[0]:
            return 'Cygwin'
        else:
            self.message("Unsupported Platform ("+os.uname()[0]+").",2)
            self.exit_gracefully(1)
    
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
            # Set options to force dts-audio
            if options.forcedts:
                self.options['forcedts'] = True
            else:
                self.options['forcedts'] = False
            
            if options.nocrop:
                self.options['nocrop'] = True
            else:
                self.options['nocrop'] = False

            # Set options to force x265-encoder
            if options.forcex265:
                self.options['forcex265'] = True
            else:
                self.options['forcex265'] = False

            # Keep temp (debug)
            if options.keeptemp:
                self.options['keeptemp'] = True
            else:
                self.options['keeptemp'] = False

            # Set options to force vp9-encoder
            if options.vp9:
                self.options['vp9'] = True
            else:
                self.options['vp9'] = False
            
            if options.disable_maxrate:
                self.options['disable_maxrate'] = True
            else:
                self.options['disable_maxrate'] = False

            if options.snap:
                self.options['snap'] = True
            else:
                self.options['snap'] = False

            # Set output directory
            if options.outdir:
                if os.path.exists(options.outdir):
                    self.options['outdir'] = options.outdir
                else:
                    self.message("Output directory does not exist.",2)
                    self.exit_gracefully(1)
            else:
                self.options['outdir'] = os.getcwd()+"/output"
            
            # Store files in the same directory as original
            if options.nooutdir:
                self.options['nooutdir'] = True
            else:
                self.options['nooutdir'] = False

            self.options['availCPU'] = self.available_cpu_count()

            # Handle cpu-threads
            if options.threads:
                availCPU = self.available_cpu_count()
                if options.threads > availCPU:
                    self.options['threads'] = availCPU
                else:
                    self.options['threads'] = max(0, options.threads)
                    
                if self.options['threads'] == 0:
                    self.message("Using "+O+"all"+W+" threads.",1)
                else:
                    self.message("Using "+O+str(self.options['threads'])+W+"/"+O+str(availCPU)+W+" threads.",1)
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
        command_group.add_argument('--vp9',help='Force use of vp9-encoder', action='store_true',dest='vp9')
        command_group.add_argument('--disable_maxrate',help='Disables x264-maxrate', action='store_true',dest='disable_maxrate')
        command_group.add_argument('--nocrop',help='Disable cropping.',action='store_true',dest='nocrop')
        command_group.add_argument('--nooutdir',help='Store new files in the same directory as original.',action='store_true',dest='nooutdir')
        command_group.add_argument('--outdir',help='Output directory',action='store',dest='outdir')
        command_group.add_argument('--snap',help='Converts first five minutes.',action='store_true',dest='snap')
        command_group.add_argument('--threads',help='Number of threads',action='store',type=int,dest='threads')
        command_group.add_argument('--keeptemp',help='Debug: Keep Temp-Directory',action='store_true',dest='keeptemp')
        return option_parser

    def sizeof_fmt (self, num, suffix='B'):
        for unit in ['','K','M','G','T','P','E','Z']:
            if abs(num) < 1024.0:
                return "%3.1f%s%s" % (num, unit, suffix)
            num /= 1024.0
        return "%.1f%s%s" % (num, 'Yi', suffix)

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
        if os.path.exists(self.options['temp']) and not self.options['keeptemp']:
            rmtree(self.options['temp'])
        print (R+" [!]"+W+" quitting.")
        exit(code)
        
class PacvertMedia:
    """
        Holds data for a Media and perfoms actions
    """
    def __init__(self, pacvertFile, pacvertConfig):
        self.pacvertFile = pacvertFile
        self.pacvertPath = os.path.dirname(self.pacvertFile)
        self.pacvertName = os.path.basename(self.pacvertFile)
        self.pacvertFilesize = os.stat(self.pacvertFile).st_size
        self.config = pacvertConfig
        self.streams = []
        self.format = PacvertMediaFormatInfo()
        self.streammap = []
        self.streamopt = []
        self.addFiles = []

        self.pacvertFileExtensions = self.config.get("FileSettings","FileFormat") \
        if self.config.get("FileSettings","FileFormat") != "" \
        else "mkv" if self.pacvertFilesize > 5000000000 else "m4v"

    def analyze(self,tools,options):
        """
            use ffprobe to add all streams to this object.
        """
        if not options['silent']:
            self.message(B+"Creating new job configuration:")
            self.message(O+"  * "+W+"Filename:\t"+self.pacvertName)
            self.message(O+"  * "+W+"Filesize:\t"+self.sizeof_fmt(self.pacvertFilesize))
        
        #calling ffprobe
        cmd = [tools['ffprobe'],'-show_format','-show_streams',self.pacvertFile]
        proc_ffprobe = Popen(cmd, shell=False,stdin=PIPE,stdout=PIPE,stderr=PIPE,close_fds=True)
        stdout_data, _ = proc_ffprobe.communicate()
        proc_ffprobe = str(stdout_data.decode("UTF-8").encode('ascii', 'ignore')).replace("\\n","\n")

        in_format = False
        current_stream = None

        for line in proc_ffprobe.split("\n"):
            if "[STREAM]" in line:
                current_stream = PacvertMediaStreamInfo()
            elif "[/STREAM]" in line:
                if current_stream.type:
                    self.streams.append(current_stream)
                current_stream = None
            elif "[FORMAT]" in line:
                in_format = True
            elif "[/FORMAT]" in line:
                in_format = False
            elif "=" in line:
                k, v = line.split('=', 1)
                k = k.strip()
                v = v.strip()
                if current_stream:
                    current_stream.parse_ffprobe(current_stream, k, v)
                elif in_format:
                    self.format.parse_ffprobe(k, v)
            
    def analyze_video(self, tools, options):
        """
            analyze gathered streams for
            video, audio and subtitles
        """
        if not options['silent']:
            self.message(O+"  * "+W+"Video track:")
        
        #check for crf value
        cmd = [tools['mediainfo'],"--Output=Video;%Encoded_Library_Settings%",self.pacvertFile]
        proc_mediainfo = Popen(cmd,shell=False,stdin=PIPE,stdout=PIPE,stderr=PIPE,close_fds=True)
        
        stdout_data, _ = proc_mediainfo.communicate()
        proc_mediainfo = stdout_data.decode("UTF-8").split(' / ')

        crf = 0.0

        for b in proc_mediainfo:
            if b.split('=')[0] == "crf":
                crf = float(b.split('=')[1].replace(',','.'))
                if not options['silent']:
                    self.message(B+"    + "+W+"-source CRF: "+str(crf))

        #unset
        cmd = None
        proc_mediainfo = None
        stdout_data = None

        #check for existing bitrate
        cmd = [tools['mediainfo'],"--Output=Video;%BitRate%",self.pacvertFile]
        proc_mediainfo = Popen(
            cmd,
            shell=False,
            stdin=PIPE,
            stdout=PIPE,
            stderr=PIPE,
            close_fds=True
        )
        try:
            bitrate = int(proc_mediainfo.communicate()[0].decode('UTF-8'))
        except:
            bitrate = 0
        for c in self.streams:
            #Videostream ignore png streams!
            if c.type == "video" and c.codec != "png" and c.codec != "mjpeg":
                if c.nb_frames > 0:
                    self.frames = round(c.nb_frames)+1
                else:
                    try:
                        if c.duration > 0:
                            self.frames = round(c.duration*c.video_fps)+1
                        elif c.duration == 0 and self.format.duration > 0:
                            self.frames = round(self.format.duration*c.video_fps)+1
                        else:
                            self.frames = 1
                    except TypeError:
                        self.frames = 1
                        
                self.streammap.append("-map 0:"+str(c.index))
                if not options['silent']:
                    self.message(B+"    + "+W+"-map 0:"+str(c.index))
                
                tempIdx = len(self.streamopt)
                
                if options['forcex265']:
                    #Forcing x265...
                    self.streamopt.append("-c:v:0 libx265")
                    self.streamopt.append("-preset "+options['config'].get("VideoSettings","x265preset"))
                    if options['config'].get("VideoSettings","x265tune") != "":
                        self.streamopt.append("-tune "+options['config'].get("VideoSettings","x265tune"))
                    
                    self.streamopt.append("-crf "+options['config'].get("VideoSettings","x265crf"))
                    
                    x265params = options['config'].get("VideoSettings","x265params")
                    
                    if not options['disable_maxrate']:
                        if x265params != "":
                            x265params += ":vbv-maxrate="+str(round(bitrate/1000))
                        else:
                            x265params = "vbv-maxrate="+str(round(bitrate/1000))
                        x265params += ":vbv-bufsize="+str(round((bitrate*2)/1000))
                    
                    self.streamopt.append("-x265-params "+x265params.replace("  "," "))
                    
                    if options['config'].getboolean("VideoSettings","crop") and not options['nocrop']:
                        crop=self.analyze_crop(tools)
                        self.streamopt.append("-filter:v crop="+crop)
                        
                    self.streamopt.append("-metadata:s:v:0 language="+c.language)
                elif options['vp9']:
                    self.streamopt.append("-c:v:0 libvpx-vp9")
                    self.streamopt.append("-crf "+options['config'].get("VideoSettings","crf"))
                    self.streamopt.append("-b:v "+str(bitrate)+"k")
                    self.streamopt.append("-tile-columns "+str(round(options['availCPU']/2)))
                    self.streamopt.append("-threads "+str(min(x for x in [0, options['availCPU'], options['threads']] if x is not 0)))
                    self.streamopt.append("-metadata:s:v:0 language="+c.language)

                    if options['config'].getboolean("VideoSettings","crop") and not options['nocrop']:
                        crop=self.analyze_crop(tools)
                        self.streamopt.append("-filter:v crop="+crop)
                else:
                    if crf < options['config'].getfloat("VideoSettings","CRF"):
                        self.streamopt.append("-c:v:0 libx264")
                        self.streamopt.append("-profile:v "+options['config'].get("VideoSettings","x264profile"))
                        self.streamopt.append("-level "+options['config'].get("VideoSettings","x264level"))
                        self.streamopt.append("-preset "+options['config'].get("VideoSettings","x264preset"))
                        self.streamopt.append("-tune "+options['config'].get("VideoSettings","x264tune"))
                        self.streamopt.append("-crf "+options['config'].get("VideoSettings","crf"))
                        if not options['disable_maxrate']:
                            self.streamopt.append("-maxrate "+str(round(bitrate/1000))+"k")
                            self.streamopt.append("-bufsize "+str(round((bitrate*4.5)/1000))+"k")
                        self.streamopt.append("-metadata:s:v:0 language="+c.language)
                        
                        if options['config'].getboolean("VideoSettings","crop") and not options['nocrop']:
                            crop=self.analyze_crop(tools)
                            self.streamopt.append("-filter:v crop="+crop)
                    else:
                        self.streamopt.append("-c:v:0 copy")
                        self.streamopt.append("-metadata:s:v:0 language="+c.language)
                if not options['silent']:
                    for idx in range(tempIdx,len(self.streamopt)):
                        self.message(B+"    + "+W+self.streamopt[idx])
    
    def analyze_crop(self,tools):
        from subprocess import STDOUT
        check_percent = 5
        check_frames = round(self.frames * (check_percent/100))

        crop = [0,0,0,0]
        pbar = ProgressBar(widgets=[G+' [',AnimatedMarker(),'] '+B+'    + '+W+'Analyzing cropping rectangle.\t']).start()
        cmd = [tools['ffmpeg'],"-i",self.pacvertFile,"-vframes",str(check_frames),"-vf","cropdetect=24:16:0","-f", "null", "-"]
        proc_ffmpeg = check_output(cmd, stderr=STDOUT)
        for c in str(proc_ffmpeg.decode("ISO-8859-1")).split('\n'):
            if "crop=" in c:
                temp_crop = c.split(" ")[13].replace("crop=","").split(":")
                try:
                    if int(temp_crop[0]) > crop[0]:
                        crop[0] = int(temp_crop[0])
                        crop[2] = int(temp_crop[2])
                
                    if int(temp_crop[1]) > crop[1]:
                        crop[1] = int(temp_crop[1])
                        crop[3] = int(temp_crop[3])
                except ValueError:
                    """"""            

        pbar.finish()
        return str(crop[0])+":"+str(crop[1])+":"+str(crop[2])+":"+str(crop[3])
             
    def analyze_audio(self, tools, options):
        """
            analyze gathered streams for
            video, audio and subtitles
        """
        audCount = 0
                
        for c in self.streams:	
            if c.type == "audio":
                tempIdx = len(self.streamopt)
                defaultAudioCodec = options['config'].get("AudioSettings","DefaultAudioCodec")
                
                defaultAudioCodec.replace(" ","")
                
                if options['forcedts']:
                    defaultAudioCodec = "dts"
                
                if self.pacvertFileExtensions == "mkv" and defaultAudioCodec == "":
                    #Not forcing any audio codec
                    
                    doubleLang = False
                    for d in self.streams:
                        if d.type == "audio" and ((c.codec == "ac3" and d.codec == "aac") or (c.codec == "aac" and d.codec == "ac3")) and c.language == d.language:
                            doubleLang = True
                    if (c.codec == "dca" or c.codec == "truehd" or c.codec == "ac3" or c.codec == "eac3"):
                        self.message(O+"  * "+W+"Audio track #"+str(audCount+1)+":")
                        self.streammap.append("-map 0:"+str(c.index))
                        self.message(B+"    + "+W+"-map 0:"+str(c.index))
                        self.streamopt.append("-c:a:"+str(audCount)+" copy")
                        self.streamopt.append("-metadata:s:a:"+str(audCount)+" language="+c.language)
                        audCount+=1
                    elif (c.codec != "dca" and c.codec != "truehd" and c.codec != "ac3" and c.codec != "eac3") and doubleLang == False:
                        self.message(O+"  * "+W+"Audio track #"+str(audCount+1)+":")
                        self.streammap.append("-map 0:"+str(c.index))
                        self.message(B+"    + "+W+"-map 0:"+str(c.index))
                        self.streamopt.append("-c:a:"+str(audCount)+" "+options['config'].get("AudioSettings","ac3lib"))
                        self.streamopt.append("-b:a:"+str(audCount)+" 640k")
                        self.streamopt.append("-ac:"+str(audCount)+" "+str(min(max(2,c.audio_channels),6)))
                        self.streamopt.append("-metadata:s:a:"+str(audCount)+" language="+c.language)
                        audCount+=1
                    for idx in range(tempIdx,len(self.streamopt)):				
                        self.message(B+"    + "+W+self.streamopt[idx])
                elif self.pacvertFileExtensions == "mkv" and defaultAudioCodec != "":
                    #Forcing an audio codec
                    
                    doubleLang = False
                    for d in self.streams:
                        if d.type == "audio" and ((c.codec == "ac3" and d.codec == "aac") or (c.codec == "aac" and d.codec == "ac3")) and c.language == d.language:
                            doubleLang = True
                    
                    if defaultAudioCodec == "ac3" and c.codec != "ac3" and doubleLang == False:
                        self.message(O+"  * "+W+"Audio track #"+str(audCount+1)+":")
                        self.streammap.append("-map 0:"+str(c.index))
                        self.message(B+"    + "+W+"-map 0:"+str(c.index))
                        self.streamopt.append("-c:a:"+str(audCount)+" "+options['config'].get("AudioSettings","ac3lib"))
                        self.streamopt.append("-b:a:"+str(audCount)+" 640k")
                        self.streamopt.append("-ac:"+str(audCount)+" "+str(min(max(2,c.audio_channels),6)))
                        self.streamopt.append("-metadata:s:a:"+str(audCount)+" language="+c.language)
                        audCount+=1
                    elif defaultAudioCodec == "dts" and c.codec != "dca" and doubleLang == False:
                        self.message(O+"  * "+W+"Audio track #"+str(audCount+1)+":")
                        self.streammap.append("-map 0:"+str(c.index))
                        self.message(B+"    + "+W+"-map 0:"+str(c.index))
                        self.streamopt.append("-c:a:"+str(audCount)+" "+options['config'].get("AudioSettings","dtslib"))
                        self.streamopt.append("-metadata:s:a:"+str(audCount)+" language="+c.language)
                        audCount+=1
                    elif (defaultAudioCodec == "ac3" and c.codec == "ac3") or (defaultAudioCodec == "dts" and c.codec == "dca"):
                        self.message(O+"  * "+W+"Audio track #"+str(audCount+1)+":")
                        self.streammap.append("-map 0:"+str(c.index))
                        self.message(B+"    + "+W+"-map 0:"+str(c.index))
                        self.streamopt.append("-c:a:"+str(audCount)+" copy")
                        self.streamopt.append("-metadata:s:a:"+str(audCount)+" language="+c.language)
                        audCount+=1
                    else:
                        raise ValueError("Invalid DefaultAudioCodec in AudioSettings in config file.")
                    for idx in range(tempIdx,len(self.streamopt)):				
                        self.message(B+"    + "+W+self.streamopt[idx])
                elif (self.pacvertFileExtensions == "m4v") and (c.codec == "ac3" or c.codec == "aac"):
                    doubleLang = 0
                    for d in self.streams:
                        if d.type == "audio" and ((c.codec == "ac3" and d.codec == "aac") or (c.codec == "aac" and d.codec == "ac3")) and c.language == d.language:
                            doubleLang = 1
                    self.message(O+"  * "+W+"Audio track #"+str(audCount+1)+":")
                    self.streammap.append("-map 0:"+str(c.index))
                    self.message(B+"    + "+W+"-map 0:"+str(c.index))
                    
                    if doubleLang == 0 and c.codec == "ac3":
                        self.streamopt.append("-c:a:"+str(audCount)+" "+options['config'].get("AudioSettings","aaclib"))
                        self.streamopt.append("-b:a:"+str(audCount)+" 320k")
                        self.streamopt.append("-ac:"+str(audCount+1)+" 2")
                        self.streamopt.append("-metadata:s:a:"+str(audCount)+" language="+c.language)
                        audCount+=1
                        
                        #Output
                        for idx in range(tempIdx,len(self.streamopt)):				
                            self.message(B+"    + "+W+self.streamopt[idx])
                        tempIdx = len(self.streamopt)
                        
                        self.message(O+"  * "+W+"Audio track #"+str(audCount+1)+":")
                        self.streamopt.append("-c:a:"+str(audCount)+" copy")
                        self.streamopt.append("-metadata:s:a:"+str(audCount)+" language="+c.language)
                        audCount+=1
                        
                        #Output
                        for idx in range(tempIdx,len(self.streamopt)):				
                            self.message(B+"    + "+W+self.streamopt[idx])
                        tempIdx = len(self.streamopt)
                        
                    elif doubleLang == 0 and c.codec == "aac":
                        self.streamopt.append("-c:a:"+str(audCount)+" copy")
                        self.streamopt.append("-metadata:s:a:"+str(audCount)+" language="+c.language)
                        audCount+=1
                        
                        #Output
                        for idx in range(tempIdx,len(self.streamopt)):				
                            self.message(B+"    + "+W+self.streamopt[idx])
                        tempIdx = len(self.streamopt)
                        
                        self.message(O+"  * "+W+"Audio track #"+str(audCount+1)+":")
                        self.streamopt.append("-c:a:"+str(audCount)+" "+options['config'].get("AudioSettings","ac3lib"))
                        self.streamopt.append("-b:a:"+str(audCount)+" 640k")
                        self.streamopt.append("-ac:"+str(audCount+1)+" "+str(min(max(2,c.audio_channels),6)))
                        self.streamopt.append("-metadata:s:a:"+str(audCount)+" language="+c.language)
                        audCount+=1
                        #Output
                        for idx in range(tempIdx,len(self.streamopt)):				
                            self.message(B+"    + "+W+self.streamopt[idx])
                        tempIdx = len(self.streamopt)
                    else:
                        self.streamopt.append("-c:a:"+str(audCount)+" copy")
                        self.streamopt.append("-metadata:s:a:"+str(audCount)+" language="+c.language)
                        audCount+=1
                else:
                    self.message(O+"  * "+W+"Audio track #"+str(audCount+1)+":")
                    self.streamopt.append("-c:a:"+str(audCount)+" "+options['config'].get("AudioSettings","aaclib"))
                    self.streamopt.append("-b:a:"+str(audCount)+" 320k")
                    self.streamopt.append("-ac:"+str(audCount+1)+" 2")
                    self.streamopt.append("-metadata:s:a:"+str(audCount)+" language="+c.language)
                    
                    #Output
                    for idx in range(tempIdx,len(self.streamopt)):				
                        self.message(B+"    + "+W+self.streamopt[idx])
                    tempIdx = len(self.streamopt)
                    
                    audCount+=1
                    self.message(O+"  * "+W+"Audio track #"+str(audCount+1)+":")
                    self.streamopt.append("-c:a:"+str(audCount)+" "+options['config'].get("AudioSettings","ac3lib"))
                    self.streamopt.append("-b:a:"+str(audCount)+" 640k")
                    self.streamopt.append("-ac:"+str(audCount+1)+" "+str(min(max(2,c.audio_channels),6)))
                    self.streamopt.append("-metadata:s:a:"+str(audCount)+" language="+c.language)
                    audCount+=1
                    
                    #Output
                    for idx in range(tempIdx,len(self.streamopt)):				
                        self.message(B+"    + "+W+self.streamopt[idx])
    
    def analyze_subtitles(self, tools, options):
        """
            analyze gathered streams for
            video, audio and subtitles
        """
        subCount = 0
        for c in self.streams:
            if c.type == "subtitle":
                tempIdx = len(self.streamopt)
                self.message(O+"  * "+W+"Subtitle track #"+str(subCount+1)+":"+W)
                if (self.pacvertFileExtensions == "mkv" and (c.codec == "ass" or c.codec == "srt" or c.codec == "ssa")) \
                or (self.pacvertFileExtensions == "m4v" and c.codec == "mov_text"):
                    self.streammap.append("-map 0:"+str(c.index))
                    self.streamopt.append("-c:s:"+str(subCount)+" copy")
                    self.streamopt.append("-metadata:s:s:"+str(subCount)+" language="+c.language)
                    subCount+=1
                elif (self.pacvertFileExtensions == "mkv" and c.codec in ["pgssub","dvdsub","hdmv_pgs_subtitle","dvd_subtitle"]):
                    #Convert to SRT
                    newSub=self.convert_subtitle(c.index,c.language,c.codec,tools,options)
                    if newSub != "":
                        self.addFiles.append(newSub)
                        self.streammap.append("-map "+str(len(self.addFiles))+":0")
                        self.streamopt.append("-c:s:"+str(subCount)+" copy")
                        self.streamopt.append("-metadata:s:s:"+str(subCount)+" language="+c.language)
                        subCount+=1
                    else:
                        self.message(B+"    + "+W+" Skipping subtitle.",2)
                elif (self.pacvertFileExtensions == "m4v" and c.codec in ["pgssub","dvdsub","hdmv_pgs_subtitle","dvd_subtitle"]):
                    #Convert to mov_text
                    newSub=self.convert_subtitle(c.index,c.language,c.codec,tools,options)
                    if newSub != "":
                        self.streammap.append("-map "+str(len(self.addFiles))+":0")
                        self.streamopt.append("-c:s:"+str(subCount)+" mov_text")
                        self.streamopt.append("-metadata:s:s:"+str(subCount)+" language="+c.language)
                        subCount+=1
                    else:
                        self.message(B+"    + "+W+" Skipping subtitle.",2)
                else:
                    if c.codec not in ["dvb_teletext","dvbsub","unknown"]:
                        self.streammap.append("-map 0:"+str(c.index))
                        if self.pacvertFileExtensions == "mkv":
                            self.streamopt.append("-c:s:"+str(subCount)+" srt")
                            self.streamopt.append("-metadata:s:s:"+str(subCount)+" language="+c.language)
                            subCount+=1
                        else:
                            self.streamopt.append("-c:s:"+str(subCount)+" mov_text")
                            self.streamopt.append("-metadata:s:s:"+str(subCount)+" language="+c.language)
                            subCount+=1
                    else:
                        self.message(B+"    + "+W+" Bad or unknown codec. Skipping subtitle.",2)
                for idx in range(tempIdx,len(self.streamopt)):
                    self.message(B+"    + "+W+self.streamopt[idx])
    
    def convert_subtitle_step1(self,cmds,timeout=20):
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
                p = Popen(cmds,shell=False,stdin=PIPE,stdout=PIPE,stderr=PIPE,close_fds=True,bufsize=10)
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
                    raise PacvertError(line.split(':')[0], cmd, total_output,pid=p.pid)
                if not yielded:
                    raise PacvertError('Unknown mkvextract error', cmd,total_output, line, pid=p.pid)
            if p.returncode != 0:
                raise PacvertError('Exited with code %d' % p.returncode,cmd,total_output, pid=p.pid)
        
    def convert_subtitle_step2(self,cmds,timeout=20):
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
                raise PacvertError(line.split(':')[0], cmd, total_output,pid=p.pid)
            if not yielded:
                raise PacvertError('Unknown bdsup2subpp error', cmd,total_output, line, pid=p.pid)
        if p.returncode != 0:
            raise PacvertError('Exited with code %d' % p.returncode,cmd,total_output, pid=p.pid)			
    
    def convert_subtitle_step3(self,cmds,tools,timeout=20):
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
            test = Popen([tools['tesseract'], "--list-langs"], stdout=PIPE, stderr=PIPE)
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
                if not "Wrote Subtitles to" in total_output:
                    raise ToolConvertError('Unknown vobsub2srt error', cmd,total_output, line, pid=p.pid)
        if p.returncode != 0:
            raise ToolConvertError('Exited with code %d' % p.returncode,cmd,total_output, pid=p.pid)

    
    def convert_subtitle(self,index,lang,codec,tools,options,timeout=10):
        """
            Converts subtitle to srt
        """
        tempFileName=options['temp']+os.path.splitext(self.pacvertName)[0]+"."+str(index)
        tempFileName = tempFileName.replace(" ","_")
        tempFileName = tempFileName.replace("\"","_")
        tempFileName = tempFileName.replace("\'","_")
        
        if codec not in ["dvdsub","dvd_subtitle"]:
            cmd_mkvextract=[tools['mkvextract'],"tracks",self.pacvertFile,str(index)+":"+tempFileName+".sup"]
        else:
            cmd_mkvextract=[tools['mkvextract'],"tracks",self.pacvertFile,str(index)+":"+tempFileName+".sub"]
            
        cmd_bdsup2subpp=[tools['bdsup2subpp'],"-o",tempFileName+".sub",tempFileName+".sup"]
        
        if os.path.isdir("/usr/share/tessdata"):
            tessdata = "/usr/share/tessdata"
        else:
            tessdata = "/usr/local/share/tessdata"
        
        cmd_vobsub2srt=[tools['vobsub2srt'],"--tesseract-lang",lang,"--tesseract-data",tessdata,tempFileName,"--verbose"]

        #on error, skip subtitle
        try:
            #First Block, let's extract the subtitle from file.
            widgets = [G+' [',AnimatedMarker(),']','     '+B+'+'+W+' Extracting subtitle:\t',Percentage(),' (',ETA(),')']
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

            #Second Block, extract frames from subtitle
            if codec not in ["dvdsub","dvd_subtitle"]:
                widgets = [G+' [',AnimatedMarker(),']','     '+B+'+'+W+' Extracting frames:\t',Percentage(),' (',ETA(),')']
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
            length=0
            ins = open(tempFileName+'.idx', "r")
            for line in ins:
                if "timestamp" in line:
                    length+=1
            
            widgets = [G+' [',AnimatedMarker(),']','     '+B+'+'+W+' OCR on frames:\t',Percentage(),' (',ETA(),')']
            pbar = ProgressBar(widgets=widgets, maxval=length)
            pbar.start()
            
            step3 = self.convert_subtitle_step3(cmd_vobsub2srt,tools)
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

            #Remove in the previous step extracted sub/sup
            if os.path.isfile(tempFileName+".sub"):
                os.remove(tempFileName+".sub")
            if os.path.isfile(tempFileName+".sup"):
                os.remove(tempFileName+".sup")
            
            if os.path.isfile(tempFileName+".srt"):
                if sum (1 for line in open(tempFileName+".srt")) > 5:
                    return tempFileName+".srt"
        except:
            try:
                pbar.finish()
                return ""
            except:
                return ""
                
        return ""
    
    def getFlags(self,tools):
        cmd = []
        cmd.append(tools['ffmpeg'])
        cmd.append("-i")
        cmd.append(self.pacvertFile)
        for i in self.addFiles:
            cmd.append("-i")
            cmd.append(i)
            
        for i in self.streammap:
            cmd.extend(i.split(" "))
        
        for i in self.streamopt:
            cmd.extend(i.split(" "))
        
        return cmd

    def convert(self,tools,options,timeout=10):
        if not os.path.exists(self.pacvertFile):
            raise Exception("Input file doesn't exists: "+self.pacvertFile)

        #Output Directory
        if options['nooutdir']:
            outdir = self.pacvertPath
            outfile = outdir+"/"+os.path.splitext(self.pacvertName)[0]+"-new."+self.pacvertFileExtensions
        else:
            outdir = options['outdir']
            outfile = outdir+"/"+os.path.splitext(self.pacvertName)[0]+"."+self.pacvertFileExtensions

        if not os.path.exists(outdir):
            os.makedirs(outdir)

        cmds = self.getFlags(tools)
        cmds.extend(['-y', '-threads',str(options['threads'])])
        if options['snap']:
            cmds.extend(['-t', '00:05:00'])

        cmds.append(outfile)

        if timeout:
            def on_sigalrm(*_):
                signal.signal(signal.SIGALRM,signal.SIG_DFL)
                raise PacvertError("Timed out while waiting for ffmpeg","","")
            signal.signal(signal.SIGALRM,on_sigalrm)

        try:
            p = Popen(cmds,shell=False,stdin=PIPE,stdout=PIPE,stderr=PIPE,close_fds=True,universal_newlines=True)
        except OSError:
            raise PacvertError("Error while calling ffmpeg binary","","")
        
        yielded = False
        buf = ""
        total_output = ""
        pat = re.compile(r'frame=\s*(-?[0-9]+)\s*fps=\s*(-?[0-9]+)')
        while True:
            if timeout:
                signal.alarm(timeout)

            ret = p.stderr.read(10)

            if timeout:
                signal.alarm(0)

            if not ret:
                break
            
            total_output += ret
            buf += ret
            if "\n" in buf:
                line,buf = buf.split("\n", 1)

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
                raise PacvertError(line.split(':')[0], cmd, total_output,pid=p.pid)
            if line.startswith(self.pacvertPath + ': '):
                err = line[len(self.pacvertPath) + 2:]
                raise PacvertError('Encoding error',cmd,total_output,err,pid=p.pid)
            if line.startswith('Error while '):
                raise PacvertError('Encoding error',cmd,total_output,line,pid=p.pid)
            if not yielded:
                raise PacvertError('Unknown ffmpeg error', cmd,total_output, line, pid=p.pid)
        if p.returncode != 0:
            raise PacvertError('Exited with code %d' % p.returncode,cmd,total_output, pid=p.pid)
            
    def check_sanity(self,tools,options):
        """
        """
        # Disabling cropping to speed up things.
        old_c = self.config.getboolean("VideoSettings","Crop")
        self.config.set("VideoSettings","CROP","False")
        
        #Output Directory
        if options['nooutdir']:
            outdir = self.pacvertPath
            output = outdir+"/"+os.path.splitext(self.pacvertName)[0]+"-new."+self.pacvertFileExtensions
        else:
            outdir = options['outdir']
            output = outdir+"/"+os.path.splitext(self.pacvertName)[0]+"."+self.pacvertFileExtensions
        
        if not os.path.isfile(output):
            self.message(B+"    + "+W+"Sanity Check:\t"+R+"Failed"+W+". (output doesn't exist)"+W,2)
            TOFAIL.append(self)
        else:		
            #Analyze output
            options['silent'] = True
            outputf = PacvertMedia(output,self.config)
            outputf.analyze(tools,options)
            outputf.analyze_video(tools,options)
            options['silent'] = False

            # Restore cropping
            self.config.set("VideoSettings","CROP",str(old_c))

            # Calculate difference in both files
            pre_frames = self.frames
            try:	
                new_frames = outputf.frames
            except AttributeError:
                TOFAIL.append(self)
                new_frames = -1
            diff = int(abs(pre_frames-new_frames))

            #maxdiff in Frames
            maxdiff = self.config.getint("FileSettings","MaxDiff")
            
            
            #Filesize difference
            
            oldsize = self.pacvertFilesize
            newsize = outputf.pacvertFilesize			
            
            # Proceed...
            if self.config.getboolean('FileSettings','deletefile') and diff <= maxdiff:
                self.message(B+"    + "+W+"[Sanity Check] File "+G+"Passed"+W+".")
                self.message(B+"    + "+W+"[Sanity Check] Deleting "+O+"original"+W+" file.")
                
                if newsize > oldsize:
                    self.message(B+"    + "+W+"[Sanity Check] New file gained "+O+str(self.sizeof_fmt(newsize-oldsize))+W+".")
                else:
                    self.message(B+"    + "+W+"[Sanity Check] New file lost "+O+str(self.sizeof_fmt(oldsize-newsize))+W+".")
                
                os.remove(self.pacvertFile)
                os.rename(output,str(output).replace("-new."+self.pacvertFileExtensions,"."+self.pacvertFileExtensions))
            elif self.config.getboolean('FileSettings','deletefile') and diff > maxdiff:
                self.message(B+"    + "+W+"[Sanity Check] File "+R+"Failed"+W+".",2)
                self.message(B+"    + "+W+"[Sanity Check] Max allowed difference: "+O+str(maxdiff)+W,2)
                self.message(B+"    + "+W+"[Sanity Check] Current difference: "+O+str(diff)+W,2)
                self.message(B+"    + "+W+"[Sanity Check] Keeping old & removing "+O+"NEW"+W+" file"+W,2)
                os.remove(output)
            elif not self.config.getboolean('FileSettings','deletefile') and diff <= maxdiff:
                self.message(B+"    + "+W+"[Sanity Check] File "+G+"Passed"+W+".")
                if newsize > oldsize:
                    self.message(B+"    + "+W+"[Sanity Check] New file gained "+O+str(self.sizeof_fmt(newsize-oldsize))+W+".")
                else:
                    self.message(B+"    + "+W+"[Sanity Check] New file lost "+O+str(self.sizeof_fmt(oldsize-newsize))+W+".")
                self.message(B+"    + "+W+"[Sanity Check] Keeping "+O+"old"+W+" & "+O+"new"+W+" file"+W)
            elif diff > maxdiff:
                self.message(B+"    + "+W+"[Sanity Check] File "+R+"Failed"+W+".",2)
                self.message(B+"    + "+W+"[Sanity Check] Max allowed difference: "+O+str(maxdiff)+W,2)
                self.message(B+"    + "+W+"[Sanity Check] Current difference: "+O+str(diff)+W,2)
                self.message(B+"    + "+W+"[Sanity Check] Keeping old & removing "+O+"NEW"+W+" file"+W,2)
                os.remove(output)
            
    
    def message(self, mMessage, mType = 0):
        if mType == 0:
            print(G+" [+] "+W+mMessage+W)
        elif mType == 1:
            print(O+" [-] WARNING: "+W+mMessage+W)
        elif mType == 2:
            print(R+" [!] ERROR: "+W+mMessage+W)
        else:
            self.exit_gracefully(1)
    
    def sizeof_fmt (self, num, suffix='B'):
        for unit in ['','K','M','G','T','P','E','Z']:
            if abs(num) < 1024.0:
                return "%3.1f%s%s" % (num, unit, suffix)
            num /= 1024.0
        return "%.1f%s%s" % (num, 'Yi', suffix)
        
class PacvertMediaStreamInfo(object):
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
        self.nb_frames = None

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

    @staticmethod
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
        elif key == 'nb_frames':
            self.nb_frames = self.parse_int(val)

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

class PacvertMediaFormatInfo(object):
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
            self.bitrate = PacvertMediaFormatInfo.parse_float(val, None)
        elif key == 'duration':
            self.duration = PacvertMediaFormatInfo.parse_float(val, None)
        elif key == 'size':
            self.size = PacvertMediaFormatInfo.parse_float(val, None)
    
    @staticmethod
    def parse_float(val, default=0.0):
        try:
            return float(val)
        except:
            return default

    def __repr__(self):
        if self.duration is None:
            return 'PacMediaFormatInfo(format=%s)' % self.format
        return 'PacMediaFormatInfo(format=%s, duration=%.2f)' % (self.format,self.duration)

if __name__ == '__main__':
    Pacvert()
