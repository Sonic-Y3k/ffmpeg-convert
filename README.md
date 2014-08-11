Pacvert
==============
An automated video conversion tool.

About
-----
*pacvert is only for linux or mac os x*

pacvert searches files to convert recursively in the current folder and batch converts them to a m4v or mkv container.

Execution
---------
To download and execute pacvert, run the commands below:

>
    `wget https://raw.githubusercontent.com/Sonic-Y3k/ffmpeg-convert/master/pacvert.py`  
    `chmod +x https://raw.githubusercontent.com/Sonic-Y3k/ffmpeg-convert/master/pacvert.py`  
    `./pacvert.py`  

Usage:
------
>
    usage: pacvert.py [-h] [--chown CHOWN] [--crf CRF] [--ext {m4v,mkv}]
                      [--nocrop] [--outdir DIRECTORY] [--rmfile] [--shutdown]
                      [--x264level {1,1b,1.1,1.2,1.3,2,2.1,2.2,3,3.1,3.2,4,4.1,4.2,5,5.1}]
                      [--x264preset {ultrafast,superfast,veryfast,faster,fast,medium,slow,slower,veryslow,placebo}]
                      [--x264profile {baseline,main,high,high10,high422,high444}]
                      [--x264tune {film,animation,grain,stillimage,psnr,ssim,fastdecode,zerolatency}]
>    
    optional arguments:
      -h, --help
>    
>
    COMMAND:
    --chown CHOWN         Change output user.
    --crf CRF             Change crf-video value to <float>.
    --ext {m4v,mkv}       Change output extension.
    --nice NICE           Change nice value.
    --nocrop              Disable cropping
    --outdir DIRECTORY    Change outdir to <directory>.
    --rmfile              Remove original video.
    --shutdown            Shutdown after finishing all jobs.
    --x264level {1,1b,1.1,1.2,1.3,2,2.1,2.2,3,3.1,3.2,4,4.1,4.2,5,5.1}
                          Change x264-level
    --x264preset {ultrafast,superfast,veryfast,faster,fast,medium,slow,slower,veryslow,placebo}
                          Change x264-preset
    --x264profile {baseline,main,high,high10,high422,high444}
                          Change x264-profile
    --x264tune {film,animation,grain,stillimage,psnr,ssim,fastdecode,zerolatency}
                          Change x264-tune

Default Options
---------------
* crf = 18
* ext = m4v for files < 5GB and mkv for files > 5gb
* x264level = 4.1
* x264preset = slow
* x264profile = high
* x264tune = film

Note: By creating m4v-files the audio stream layout will look like this:
* map 0:1 to 0:1 AAC
* map 0:1 to 0:2 AC3
* map 0:2 to 0:3 AAC
* map 0:2 to 0:4 AC3

Required Programs
-----------------
* [python2](https://www.python.org/) - Pacvert is a Python script and requires Python to run.
* [python2-progressbar2](https://pypi.python.org/pypi/progressbar2) - Text progress bar library for Python.
* [ffmpeg](https://www.ffmpeg.org/) - For converting
* [mplayer](www.mplayerhq.hu/) - For calculating the crop area
* [mkvextract](https://www.bunkus.org/videotools/mkvtoolnix/) - Part of the mkvtoolnix suite
* [bdsup2sub](http://forum.doom9.org/showthread.php?p=1613303) - For converting bluray subtitles to vobsub
* [tesseract](http://code.google.com/p/tesseract-ocr/) - OCR Software, needs to be installed with all languages
* [vobsub2srt](https://github.com/ruediger/VobSub2SRT) - Converting vobsub to srt

Licensing
---------
Pacvert is licensed under the GNU General Public License version 2 (GNU GPL v2).

(C) 2014 Sonic-Y3k
