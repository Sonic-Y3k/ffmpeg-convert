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
    usage: pacvert.py [-h] [--forcedts] [--forcex265] [--outdir OUTDIR] [--threads THREADS]
    
>    
    optional arguments:
      -h, --help       show this help message and exit
>    
>
    COMMAND:
        --forcedts       Force use of dts-codec
        --forcex265      Force use of x265-encoder
        --outdir OUTDIR  Output directory
        --threads THREADS Number of threads


Default pacvert.conf:
------
>

    [ConfigVersion]
    version = 4.0

    [FileSettings]
    deletefile = True
    fileformat = 
    searchextensions = avi,flv,mov,mp4,mpeg,mpg,ogv,wmv,m2ts,rmvb,rm,3gp,m4v,3g2,mj2,asf,divx,vob,mkv
    maxdiff = 50

    [VideoSettings]
    crf = 18.0
    crop = True
    x264level = 4.1
    x264preset = slow
    x264profile = high
    x264tune = film
    x265preset = slow
    x265tune = 
    x265params = 
    x265crf = 23.0

    [AudioSettings]
    defaultaudiocodec = 
    aaclib = aac -strict -2
    ac3lib = ac3
    dtslib = dca -strict -2

Note
---------------
* If no fileformat (m4v / mkv) is specified, pacvert will chose m5v for files < 5GB and mkv for files > 5gb 
* m4v audio layout:
    * map 0:1 to 0:1 AAC
    * map 0:1 to 0:2 AC3
    * map 0:2 to 0:3 AAC
    * map 0:2 to 0:4 AC3

Required Programs
-----------------
* [python](https://www.python.org/) - Pacvert is a Python script and requires Python to run.
* [python-progressbar2](https://pypi.python.org/pypi/progressbar2) - Text progress bar library for Python.
* [ffmpeg](https://www.ffmpeg.org/) - For converting
* [mplayer](www.mplayerhq.hu/) - For calculating the crop area
* [mkvextract](https://www.bunkus.org/videotools/mkvtoolnix/) - Part of the mkvtoolnix suite
* [bdsup2sub](http://forum.doom9.org/showthread.php?p=1613303) - For converting bluray subtitles to vobsub
* [tesseract](http://code.google.com/p/tesseract-ocr/) - OCR Software, needs to be installed with all languages
* [vobsub2srt](https://github.com/ruediger/VobSub2SRT) - Converting vobsub to srt

Licensing
---------
Pacvert is licensed under the GNU General Public License version 2 (GNU GPL v2).

(C) 2014-2015 Sonic-Y3k
