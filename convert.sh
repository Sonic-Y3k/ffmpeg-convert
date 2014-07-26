#!/bin/bash
DEFAULT_PATH=""
dictPath="$(pwd)"
searchExt="avi|flv|iso|mov|mp4|mpeg|mpg|ogg|ogm|ogv|wmv|m2ts|rmvb|rm|3gp|m4a|3g2|mj2|asf|divx|vob|mkv"
crfVal="18.0"

dictTotal=1
dictProgress=0
DEFAULT_OUTPUTF=""
LOGFILE="$dictPath/log.$(date +%s).log"

f_LOG() {
	echo -e "`date`:$@" >> $LOGFILE
}

f_INFO() {
	#echo "$@"
	f_LOG "INFO: $@"
}

f_WARNING() {
	#echo "$@"
	f_LOG "WARNING: $@"
}

f_ERROR() {
	#echo "$@"
	f_LOG "ERROR: $@"
}

function showBar {
	percDone=$(echo 'scale=2;'$1/$2*100 | bc)
	barLen=`echo "30*${percDone%'.00'}/100" |bc`
	bar=''
	fills=''
	for (( b=0; b<$barLen; b++ ))
	do
		bar=$bar"#"
	done
	
	blankSpaces=$(echo $((30-$barLen)))
	for (( f=0; f<$blankSpaces; f++ ))
	do
		fills=$fills"·"
	done

	if [ $percDone = "0" ]; then
		echo -e '0'$(echo 'scale=2;'$1*100/$2 | bc)'%\t['$bar$'\e[33m''ᗧ'$'\e[00m'$fills']'
	else
		echo -e $(echo 'scale=2;'$1*100/$2 | bc)'%\t['$bar$'\e[33m''ᗧ'$'\e[00m'$fills']'
	fi
}

function getFrameCount {
	echo $(mediainfo "--Inform=Video;%FrameCount%" "$DEFAULT_PATH")
}

function getFilename {
	bname=`echo $(basename "$DEFAULT_PATH")`
	if [[ ${#bname} -gt 30  && -n "$1"  && $1 = true ]]; then
		echo "${bname:0:30}...${bname##*.}"
	else
		echo $bname
	fi
}

function getAudioInfo {
	if [ -z "$1" ]; then
		#You need to specify a Track#
		exit 0
	fi
	
	#Create ffprobe output
	ffprobe -v quiet -print_format json -show_format -show_streams "$DEFAULT_PATH" > ffprobe.txt

	if [ "$1" = "-1" ]; then
		ret=`cat ffprobe.txt |jsawk 'return this.format' |jsawk 'return this.nb_streams'`
	else
		if [[ $(cat ffprobe.txt |grep "language") = "" ]];
		then
			myl="{a:this.index,b:this.codec_name,c:this.tags.LANGUAGE,d:this.channels}"
		else
			myl="{a:this.index,b:this.codec_name,c:this.tags.language,d:this.channels}"
		fi
		
		for info in `cat ffprobe.txt |jsawk 'return this.streams' |jsawk 'if (!this.tags) return {a:this.index,b:this.codec_name,d:this.channels}' |jsawk 'if (this.tags) return '$myl'' |jsawk -n "out (this)" |sed 's/\"//g' |sed 's/{a://g' |sed 's/b://g' |sed 's/c://g' |sed 's/d://g' |sed 's/}//g'`
		do
			if [ $(echo $info|cut -d',' -f1) = "$1" ]; then
				ret="$info"
			fi
		done
	fi
	
	#Return something.
	if [ "$ret" == "" ]; then
		echo "Unknown"
	else
		echo "$ret"
	fi
	
	#Delete ffprobe.txt
	rm ffprobe.txt 
}

function getAudioLanguage {
	if [ -z "$1" ]; then
		#You need to specify a Track#
		exit 0
	fi
	
	ret=$(echo $(getAudioInfo $1)|cut -d',' -f3)
	
	if [ "$ret" != "" ];
	then
		echo $(langFix "$ret")
	else
		echo "und"
	fi
}

function getAudioCodec {
	if [ -z "$1" ]; then
		#You need to specify a Track#
		exit 0
	fi
	
	echo $(echo $(getAudioInfo $1)|cut -d',' -f2)
}

function getAudioChannels {
	if [ -z "$1" ]; then
		#You need to specify a Track#
		exit 0
	fi
	echo $(echo $(getAudioInfo $1)|cut -d',' -f4)
	
}

function getVidQuality {
	encInf=$(mediainfo --Output="Video;%Encoded_Library_Settings%" "$DEFAULT_PATH")
	crf=0.0
	for x in `echo $encInf | tr " / " "\n"`; 
	do 
		if [ "${x:0:4}" = "crf=" ];
		then 
			#CRF of Video
			crf=$(echo "${x:4:6}"|sed 's/,/\./g'); 
		fi
	done
	
	echo ${crf/./}
}

containsElement () {
	local e
	for e in "${@:2}"; do [[ "$e" == "$1" ]] && return 0; done
	return 1
}

function checkFileCodecs {
	returnMap="-loglevel panic -stats"
	returnFi=""
	subCount=0
	audCount=0
	newCount=0
	inCount=0
	
	numberOfTracks=`echo "$(getAudioInfo -1)" |bc`

	f_INFO "Analyze $numberOfTracks Tracks:"
	f_INFO "Video:"
	#Video Tracks
	for (( i=0; i<$numberOfTracks; i++ )) {
		
		currCod="$(getAudioCodec $i)"
		
		vidcodecs=("vc1" "hevc" "amv" "asv1" "asv2" "avrp" "avui" "ayuv" "bmp" "cinepak" "cljr" "dnxhd" "dpx" "dvvideo" "ffv1" "ffvhuff" "flashsv" "flashsv2" "flv1" "gif" "h261" "h263" "h263p" "h264" "huffyuv" "jpeg2000" "jpegls" "mjpeg" "mpeg1video" "mpeg2video" "mpeg4" "msmpeg4v2" "msmpeg4v3" "msvideo1" "pam" "pbm" "pcx" "pgm" "pgmyuv" "png" "ppm" "prores" "qtrle" "r10k" "r210" "rawvideo" "roq" "rv10" "rv20" "sgi" "snow" "sunrast" "svq1" "targa" "tiff" "utvideo" "v210" "v308" "v408" "v410" "wmv1" "wmv2" "xbm" "xface" "xwd" "y41p" "yuv4" "zlib")
		containsElement "$currCod" "${vidcodecs[@]}"
		testVid="$?"
		if [ "$testVid" = "0" ];
		then
			inCount=$(echo "$inCount+1"|bc)
			if [ $(printf "%d\n" $(getVidQuality)) -ge $(printf "%d\n" ${crfVal/./}) ]; then 
				returnMap="$returnMap -map 0:$(echo $i|bc)"
				returnFlag="-c:v:0 copy"
				f_INFO "-Stream #0:$i ($currCod) -> #0:$newCount (copy)"
			else
				returnMap="$returnMap -map 0:$(echo $i|bc)"
				returnFlag="-c:v:0 libx264 -profile:v high -level 4.1 -preset slow -crf $crfVal -tune film"
				f_INFO "-Stream #0:$i ($currCod) -> #0:$newCount (libx264)"
				newCount=$(echo "$newCount+1"|bc)
			fi
		fi
	}

	if [[ "$returnFlag" != *c:v:?* ]];
	then
		f_ERROR "No video track found. Stopping here."
		exit 1
	fi
	
	f_INFO "Audio:"
	#Audio Tracks
	for (( i=0; i<$numberOfTracks; i++ )) {
		currCod="$(getAudioCodec $i)"
		
		audcodecs=("truehd" "dca" "real_144" "libmp3lame" "mp2fixed" "g726" "g722" "ac3_fixed" "libfaac" "adpcm_adx" "adpcm_g722" "adpcm_g726" "adpcm_ima_qt" "adpcm_ima_wav" "adpcm_ms" "adpcm_swf" "adpcm_yamaha" "alac" "comfortnoise" "dts" "eac3" "flac" "g723_1" "mp2" "mp3" "nellymoser" "pcm_alaw" "pcm_f32be" "pcm_f32le" "pcm_f64be" "pcm_f64le" "pcm_mulaw" "pcm_s16be" "pcm_s16be_planar" "pcm_s16le" "pcm_s16le_planar" "pcm_s24be" "pcm_s24daud" "pcm_s24le" "pcm_s24le_planar" "pcm_s32be" "pcm_s32le" "pcm_s32le_planar" "pcm_s8" "pcm_s8_planar" "pcm_u16be" "pcm_u16le" "pcm_u24be" "pcm_u24le" "pcm_u32be" "pcm_u32le" "pcm_u8" "ra_144" "roq_dpcm" "s302m" "sonic" "tta" "vorbis" "wavpack" "wmav1" "wmav2")
		containsElement "$currCod" "${audcodecs[@]}"
		testAud="$?"
		
		#Output as mkv-format - just copy audio...
		if [[ $DEFAULT_OUTPUTF = *"mkv"* && ( $currCod = *"ac3"* || $currCod = *"dca"* || $currCod = *"truehd"* ) ]]; then
			returnMap="$returnMap -map 0:$i"
			returnFlag="$returnFlag -c:a:$audCount copy -metadata:s:a:$audCount language=$(getAudioLanguage $i)"
			audCount=$(echo "$audCount+1"|bc)
			f_INFO "-Stream #0:$i ($currCod - $(getAudioLanguage $i)) -> #0:$newCount (copy)"
		
		#Output as m4v-format with ac3
		elif [[ "$DEFAULT_OUTPUTF" == "m4v" && "$currCod" == "ac3" ]]; then
			#Checking for already converted audio
			doubleLang=false;
			ac3Lang="$(getAudioLanguage $i)"
			for (( j=0;j<=numberOfTracks;j++ )) do
				if [[ "$(getAudioLanguage $j)" = "$ac3Lang"  &&  "$(getAudioCodec $j)" = "aac" ]]; then
					doubleLang=true;
				fi
			done
			
			#No already converted audio found
			if [ $doubleLang = false ]; then
				returnMap="$returnMap -map 0:$i -map 0:$i"
				returnFlag="$returnFlag -c:a:$audCount libfaac -b:a:$audCount 320k -ac:"$(echo "$audCount+1"|bc)" 2 -metadata:s:a:$audCount language=$(getAudioLanguage $i)"
				f_INFO "-Stream #0:$i ($currCod - $(getAudioLanguage $i)) -> #0:$newCount (libfaac)"
				newCount=$(echo "$newCount+1"|bc)
				audCount=$(echo "$audCount+1"|bc)
				returnFlag="$returnFlag -c:a:$audCount copy -metadata:s:a:$audCount language=$(getAudioLanguage $i) -metadata:s:a:$audCount language=$(getAudioLanguage $i)"
				f_INFO "-Stream #0:$i ($currCod - $(getAudioLanguage $i)) -> #0:$newCount (copy)"
				audCount=$(echo "$audCount+1"|bc)
				newCount=$(echo "$newCount+1"|bc)
			else
				returnMap="$returnMap -map 0:$i"
				returnFlag="$returnFlag -c:a:$audCount copy -metadata:s:a:$audCount language=$(getAudioLanguage $i) -metadata:s:a:$audCount language=$(getAudioLanguage $i)"
				f_INFO "-Stream #0:$i ($currCod - $(getAudioLanguage $i)) -> #0:$newCount (copy)"
				audCount=$(echo "$audCount+1"|bc)
				newCount=$(echo "$newCount+1"|bc)
			fi
		
		#Output as m4v-format with DTS,MP3, ...
		elif [[ "$DEFAULT_OUTPUTF" = "m4v" && "$testAud" = "0" ]]; then
			returnMap="$returnMap -map 0:$i -map 0:$i"
			returnFlag="$returnFlag -c:a:$audCount libfaac -b:a:$audCount 320k -ac:"$(echo "$audCount+1"|bc)" 2 -metadata:s:a:$audCount language=$(getAudioLanguage $i)"
			f_INFO "-Stream #0:$i ($currCod - $(getAudioLanguage $i)) -> #0:$newCount (libfaac)"
			newCount=$(echo "$newCount+1"|bc)
			audCount=$(echo "$audCount+1"|bc)
			audChannels=$(getAudioChannels $i)
			returnFlag="$returnFlag -c:a:$audCount ac3 -b:a:$audCount 640k -ac:"$(echo "$audCount+1"|bc)" "$((audChannels>1?audChannels:2))" -metadata:s:a:$audCount language=$(getAudioLanguage $i)"
			f_INFO "-Stream #0:$i ($currCod - $(getAudioLanguage $i)) -> #0:$newCount (ac3)"
			newCount=$(echo "$newCount+1"|bc)
			audCount=$(echo "$audCount+1"|bc)
			
		#Output as m4v-format with AAC
		elif [[ "$DEFAULT_OUTPUTF" == "m4v" && "$currCod" == "aac" ]]; then
			#Checking for already converted audio
			doubleLang=false;
			ac3Lang="$(getAudioLanguage $i)"
			for (( j=0;j<=numberOfTracks;j++ )) do
				if [[ "$(getAudioLanguage $j)" = "$ac3Lang"  &&  "$(getAudioCodec $j)" = "ac3" ]]; then
					doubleLang=true;
				fi
			done
			
			#No already converted audio found
			if [ $doubleLang = false ]; then
				returnMap="$returnMap -map 0:$i -map 0:$i"
				returnFlag="$returnFlag -c:a:$audCount copy -metadata:s:a:$audCount language=$(getAudioLanguage $i) -metadata:s:a:$audCount language=$(getAudioLanguage $i)"
				f_INFO "-Stream #0:$i ($currCod - $(getAudioLanguage $i)) -> #0:$newCount (copy)"
				newCount=$(echo "$newCount+1"|bc)
				audCount=$(echo "$audCount+1"|bc)
				returnFlag="$returnFlag -c:a:$audCount ac3 -b:a:$audCount 640k -ac:$audCount $(getAudioChannels $i) -metadata:s:a:$audCount language=$(getAudioLanguage $i)"
				f_INFO "-Stream #0:$i ($currCod - $(getAudioLanguage $i)) -> #0:$newCount (ac3)"
				newCount=$(echo "$newCount+1"|bc)
				audCount=$(echo "$audCount+1"|bc)
			else
				returnMap="$returnMap -map 0:$i"
				returnFlag="$returnFlag -c:a:$audCount copy -metadata:s:a:$audCount language=$(getAudioLanguage $i) -metadata:s:a:$audCount language=$(getAudioLanguage $i)"
				f_INFO "-Stream #0:$i ($currCod - $(getAudioLanguage $i)) -> #0:$newCount (copy)"
				newCount=$(echo "$newCount+1"|bc)
				audCount=$(echo "$audCount+1"|bc)
			fi
		fi
	}
	
	if [[ "$returnFlag" != *c:a:0* ]];
	then
		f_ERROR "No audio track found. Stopping here."
		exit 1
	fi
	
	f_INFO "Subtitles:"
	#Subtitle Tracks
	for (( i=0; i<$numberOfTracks; i++ )) {
		currCod="$(getAudioCodec $i)"
		
		#PGP needs conversion...
		subcodecs=("pgssub" "ass" "dvdsub" "dvd_subtitle" "mov_text" "srt" "ssa" "subrip" "xsub")
		containsElement "$currCod" "${subcodecs[@]}"
		testSub="$?"
		
		#Output as mkv-format
		if [[ "$DEFAULT_OUTPUTF" = "mkv" && "$testSub" = "0" ]]; then
			returnMap="$returnMap -map 0:$i"
			returnFlag="$returnFlag -c:s:$subCount copy -metadata:s:s:$subCount language=$(getAudioLanguage $i)"
			f_INFO "-Stream #0:$i ($currCod - $(getAudioLanguage $i)) -> #0:$newCount (copy)"
			newCount=$(echo "$newCount+1"|bc)
			subCount=$(echo "$subCount+1"|bc)
		
		#Output as m4v-format
		elif [[ "$DEFAULT_OUTPUTF" = "m4v" && "$testSub" = "0" && "$currCod" != "pgssub" ]]; then
			returnMap="$returnMap -map 0:$i"
			returnFlag="$returnFlag -c:s:$subCount mov_text -metadata:s:s:$subCount language=$(getAudioLanguage $i)"
			f_INFO "-Stream #0:$i ($currCod - $(getAudioLanguage $i)) -> #0:$newCount (mov_text)"
			newCount=$(echo "$newCount+1"|bc)
			subCount=$(echo "$subCount+1"|bc)	
		
		#Output as m4v-format with pgssub
		elif [[ "$DEFAULT_OUTPUTF" = "m4v" && "$testSub" = "0" && "$currCod" == "pgssub" ]]; then
			f_INFO "-Stream #$inCount:0 ($currCod - $(getAudioLanguage $i)) -> #0:$newCount (mov_text)"
			tempFi="$(ocrPGPSubtitle $i)"
		
			if [ -n "$tempFi" ] && [ "$tempFi" != " -i " ];
			then
				f_INFO "     - Transcoded to $(echo $tempFi|sed 's:-i ::g')"
				returnMap="$returnMap -map $inCount:0"
				returnFlag="$returnFlag -c:s:$subCount mov_text -metadata:s:s:$subCount language=$(getAudioLanguage $i)"
			
 				returnFi="$returnFi$tempFi"
				newCount=$(echo "$newCount+1"|bc)
				subCount=$(echo "$subCount+1"|bc)	
				inCount=$(echo "$inCount+1"|bc)
			fi
		fi
		
	}
	echo "$returnFi $returnMap $returnFlag"
}

function langFix() {
	#Tanks to ISO 639-2 ...
	ret="$1"
	if [[ $1 == *"alb"* ]]; then ret="sqi"; fi
	if [[ $1 == *"arm"* ]]; then ret="hye"; fi
	if [[ $1 == *"baq"* ]]; then ret="eus"; fi
	if [[ $1 == *"tib"* ]]; then ret="bod"; fi
	if [[ $1 == *"bur"* ]]; then ret="mya"; fi
	if [[ $1 == *"cze"* ]]; then ret="ces"; fi
	if [[ $1 == *"chi"* ]]; then ret="zho"; fi
	if [[ $1 == *"wel"* ]]; then ret="cym"; fi
	if [[ $1 == *"ger"* ]]; then ret="deu"; fi
	if [[ $1 == *"dut"* ]]; then ret="nld"; fi
	if [[ $1 == *"gre"* ]]; then ret="ell"; fi
	if [[ $1 == *"baq"* ]]; then ret="eus"; fi	
	if [[ $1 == *"per"* ]]; then ret="fas"; fi	
	if [[ $1 == *"fre"* ]]; then ret="fra"; fi	
	if [[ $1 == *"geo"* ]]; then ret="kat"; fi	
	if [[ $1 == *"ice"* ]]; then ret="isl"; fi	
	if [[ $1 == *"mac"* ]]; then ret="mkd"; fi	
	if [[ $1 == *"mao"* ]]; then ret="mri"; fi	
	if [[ $1 == *"may"* ]]; then ret="msa"; fi	
	if [[ $1 == *"bur"* ]]; then ret="mya"; fi	
	if [[ $1 == *"per"* ]]; then ret="fas"; fi	
	if [[ $1 == *"rum"* ]]; then ret="ron"; fi	
	if [[ $1 == *"slo"* ]]; then ret="slk"; fi	
	if [[ $1 == *"tib"* ]]; then ret="bod"; fi	
	if [[ $1 == *"wel"* ]]; then ret="cym"; fi	
	if [[ $1 == *"chi"* ]]; then ret="zho"; fi	
	echo "$ret"
}

function ocrPGPSubtitle() {
	if [ -z "$1" ]; then
		#You need to specify a Track#
		exit 0
	fi

	rm -f /tmp/*.idx /tmp/*.sub /tmp/*.ps1 /tmp/*.srtx /tmp/*.sup /tmp/*.pgm /tmp/*.pgm.txt

	f_INFO "   - Need to convert subtitle"
	mytmpdir=`mktemp -d 2>/dev/null || mktemp -d -t 'pacman'`
	f_INFO "     - Setting Temp-Dir to: $mytmpdir"
	f_INFO "     - Running: mkvextract tracks \"$DEFAULT_PATH\" \"$1:$mytmpdir/track$1.sup\""
	mkvextract tracks "$DEFAULT_PATH" "$1:$mytmpdir/track$1.sup" > /dev/null 2>&1
	
	f_INFO "     - Running: bdsup2sub++ -o \"$mytmpdir/track$1.sub\" \"$mytmpdir/track$1.sup\""
	bdsup2sub++ -o "$mytmpdir/track$1.sub" "$mytmpdir/track$1.sup" > /dev/null 2>&1
	
	f_INFO "     - Running: vobsub2srt --tesseract-lang $(getAudioLanguage $i) \"$mytmpdir/track$1\""
	#vobsub2srt --tesseract-lang eng --tesseract-data /usr/local/share/tessdata "$mytmpdir/track$1"| while IFS= read -r -d $'\0' line; do
	vobsub2srt --tesseract-lang "$(getAudioLanguage $i)" "$mytmpdir/track$1" 2>&1| while IFS= read -r -d $'\0' line; do
		f_ERROR "    - $line"
	done
	
	if [ -s "$mytmpdir/track$1.srt" ]
	then
		cp "$mytmpdir/track$1.srt" "./track$1.srt"
		ret=" -i ./track$1.srt"
	else
		ret=""
	fi
	
	f_INFO "     - Deleting Temp-Dir ($mytmpdir)"
	rm -rf "$mytmpdir"
	echo "$ret"
}

function show_time () {
    num=$1
    min=0
    hour=0
    day=0
    if((num>59));then
        ((sec=num%60))
        ((num=num/60))
        if((num>59));then
            ((min=num%60))
            ((num=num/60))
            if((num>23));then
                ((hour=num%24))
                ((day=num/24))
            else
                ((hour=num))
            fi
        else
            ((min=num))
        fi
    else
        ((sec=num))
    fi
    
    if [ $hour -lt 10 ]; then
    	rethour="0"$hour
    else
    	rethour=$hour
    fi
    
    if [ $min -lt 10 ]; then
    	retmin="0"$min
    else
    	retmin=$min
    fi
    
    if [ $sec -lt 10 ]; then
    	retsec="0"$sec
    else
    	retsec=$sec
    fi
    
    echo $rethour"h "$retmin"m "$retsec"s"
}

function showFrame {
	clear
	echo -e "#  Convert with Pacman"
	echo -e "#"
	echo -e "#  Info"
	echo -e "#    Pacman-Convert:\tVersion 1.6\t\t(built on Jul 24 2014)"
	echo -e "#    ffmpeg:\t\tVersion $(ffmpeg -version |head -n1 |cut -d' ' -f3)\t\t($(ffmpeg -version |sed -n 2p|cut -d'w' -f1| awk '{$1=$1}1'|sed 's/.\{9\}$//'))"
	echo -e "#    x264:\t\tVersion $(x264 --version|head -n1| cut -d' ' -f2)\t($(x264 --version |sed -n 2p|cut -d',' -f1| awk '{$1=$1}1'))"

	echo -e "#"
	echo -e "#  Progress:"
	echo -e "#    File #:\t\t"$(($dictProgress+1))"/$dictTotal"
	echo -e "#    Filename:\t\t$(getFilename true)"
	if [ "$2" != "" ]; then
		echo -e "#    Resolution:\t$2"
	else
		echo -e "#    Resolution:\tCopying Video"
	fi
	echo -e "#    Overall:\t\t"
	cframes=$(getFrameCount)
	FR_CNT=0
	START=$(date +%s);
	ETA=0; 
	ELAPSED=0
	echo -e "#    Current File:\t"
	echo -e "#    Average FPS:\t"
	echo -e "#    ETA:\t\t"
		
	
	while [ $(ps aux | grep $1 | grep -v grep |wc -l) -gt 0 ]; do                         # Is FFmpeg running?
		if [ -f /tmp/vstats ]; then
    		VSTATS=$(awk '{gsub(/frame=/, "")}/./{line=$1-2} END{print line}' /tmp/vstats |sed 's/[^0-9]*//g')                                  # Parse vstats file.
    		if [ $(printf "%.0f" $VSTATS) -gt "$FR_CNT" ]; then                # Parsed sane or no?
    			FR_CNT=$VSTATS
    			ELAPSED=$(( $(date +%s) - START )); echo $ELAPSED > /tmp/elapsed.value
    			FPS=$(echo "$FR_CNT/$ELAPSED"|bc)
    			FPS=$(($FPS>1?$FPS:1))
    			ETA=$(show_time $(echo "($cframes-$FR_CNT)/$FPS"|bc))
    			
       			dictPer=$(echo 'scale=2;'$dictProgress+$FR_CNT/$cframes | bc)
       			tput cuu1
    			#tput el
    			tput cuu1
    			#tput el
    			tput cuu1
    			#tput el
    			tput cuu1
    			#tput el
    			echo -e "#    Overall:\t\t$(showBar ${dictPer} ${dictTotal})"
       			echo -e "#    Current File:\t$(showBar $FR_CNT $cframes)"
       			echo -e "#    Average FPS:\t$FPS"
       			echo -e "#    ETA:\t\t$ETA"
    		fi
 		fi
 		sleep 1s
	done
}

function checkSanity {
	if [[ -a "$dictPath/output/$filename.$DEFAULT_OUTPUTF" && -a "$DEFAULT_PATH" ]];
	then
		leOne=`mediainfo --Output="General;%Duration%" "$DEFAULT_PATH"`
	
		fullfile=`basename "$DEFAULT_PATH"`
		filename="${fullfile%.*}"
	
		leTwo=`mediainfo --Output="General;%Duration%" "$dictPath/output/$filename.$DEFAULT_OUTPUTF"`

		leDif=$(echo "$leOne-$leTwo"|bc)
	
		if [ $leDif -lt 0 ]; then
			leDif=$(echo "$leDif*-1"|bc)
		fi
		
		if [ $leDif -lt 250 ]; then
			#Differs by max. 250 ms... Okay delete Original.
			rm "$DEFAULT_PATH"
			rm -f ./*.srt
			f_INFO "Passed sanity check. Deleting original video."
		else
			f_WARNING "Failed sanity check (diff $leOne, $leTwo = $leDif < 250). Keep all files."
		fi
	fi

}

function calculateTotalVideos {
	dictTotal=`find -E "$dictPath" -follow -regex '.*\.('$searchExt')' 2>&1|grep -v 'Permission denied'|grep -v '/output/'|wc -l|sed 's/[^0-9]*//g'`
}

function checkDep {
	tbrew=$(which brew)
	tffmpeg=$(which ffmpeg)
	tmediainfo=$(which mediainfo)
	tmplayer=$(which mplayer)
	tmkvextract=$(which mkvextract)
	tbdsup2sub=$(which bdsup2sub++)
	ttcextract=$(which tcextract)
	tsubtitle2pgm=$(which subtitle2pgm)
	tsrttool=$(which srttool)
	ttesseract=$(which tesseract)
	tjsawk=$(which jsawk)
	tvobsub2srt=$(which vobsub2srt)
	
	#brew	
	if [ -z "$tbrew" ];
	then
		f_ERROR "brew not found."
		echo -e "Homebrew not found.\n\nPlease visit http://brew.sh/ for more information."
		exit 1
	fi

	#ffmpeg
	if [ -z "$tffmpeg" ];
	then
		f_ERROR "ffmpeg not found."
		echo -e "ffmpeg not found.\n\nPlease visit https://www.ffmpeg.org/ for more information.\n\nOr install with \"brew install ffmpeg\""
		exit 1
	fi
	
	#mediainfo 
	if [ -z "$tmediainfo" ];
	then
		f_ERROR "mediainfo not found."
		echo -e "mediainfo not found.\n\nPlease visit http://mediaarea.net/de/MediaInfo for more information.\n\nOr install with \"brew install mediainfo\""
		exit 1
	fi

	#mplayer
	if [ -z "$tmplayer" ];
	then
		f_ERROR "mplayer not found."
		echo -e "mplayer not found.\n\nPlease visit http://mplayerhq.hu/ for more information.\n\nOr install with \"brew install mplayer\""
		exit 1
	fi
	
	#mkvextract
	if [ -z "$tmkvextract" ];
	then
		f_ERROR "mkvtoolnix not found."
		echo -e "mkvtoolnix not found.\n\nPlease visit http://bunkus.org/videotools/mkvtoolnix/ for more information.\n\nOr install with \"brew install mkvtoolnix\""
		exit 1
	fi
	
	#bdsup2sub++
	if [ -z "$tbdsup2sub" ];
	then
		f_ERROR "bdsup2sub++ not found."
		echo -e "bdsup2sub++ not found.\n\nPlease visit http://forum.doom9.org/showthread.php?p=1613303 for more information.\n\nOr install with \"brew install https://raw.githubusercontent.com/Sonic-Y3k/homebrew/master/bdsup2sub++.rb\""
		exit 1
	fi
	
	#tcextract
	if [ -z "$ttcextract" ] || [ -z "$tsubtitle2pgm" ] || [ -z "$tsrttool" ]
	then
		f_ERROR "transcode not found."
		echo -e "transcode not found.\n\nPlease visit http://www.linuxfromscratch.org/blfs/view/svn/multimedia/transcode.html for more information.\n\nOr install with \"brew install https://raw.githubusercontent.com/Sonic-Y3k/homebrew/master/transcode.rb\""
		exit 1
	fi
	
	#tesseract
	if [ -z "$ttesseract" ];
	then
		f_ERROR "tesseract not found."
		echo -e "tesseract not found.\n\nPlease visit http://code.google.com/p/tesseract-ocr/ for more information.\n\nOr install with \"brew install tesseract --all-languages\""
		exit 1
	fi
	
	#jsawk
	if [ -z "$tjsawk" ];
	then
		f_ERROR "jsawk not found."
		echo -e "jsawk not found.\n\nPlease visit http://github.com/micha/jsawk for more information.\n\nOr install with \"brew install jsawk\""
		exit 1
	fi
	
	#vobsub2srt
	if [ -z "vobsub2srt" ];
	then
		f_ERROR "vobsub2srt not found."
		echo -e "vobsub2srt not found.\n\nPlease visit https://github.com/ruediger/VobSub2SRT for more information.\n\nOr install with \"brew install https://raw.githubusercontent.com/ruediger/VobSub2SRT/master/packaging/vobsub2srt.rb --HEAD vobsub2srt\""
		exit 1
	fi
	
}

function performEncode {
	checkDep
	mkdir -p "$dictPath/output"
		calculateTotalVideos
		
		f_INFO "Found $dictTotal media files."
		
		find -E "$dictPath" -follow -regex '.*\.('$searchExt')' -print0 2>&1|while IFS= read -r -d $'\0' line; do
			stripedLine=$(echo "$line"|grep -v "Permission denied"|sed ':a;N;$!ba;s/\n/ /g')
				
			if [[ $(dirname "$stripedLine") != "$dictPath/output" ]]; then
				f_INFO "Perform encode on: $stripedLine"
				DEFAULT_PATH="$stripedLine"
				startEncode
			fi
		done
}

function checkSize {
	filesize=$(wc -c "$1"|cut -d' ' -f2|sed 's/[^0-9]*//g')
	
	if [ "$DEFAULT_OUTPUTF" = "" ]
	then			
		if [ $(printf "%.0f" $filesize) -gt 5368709120 ]
		then
			DEFAULT_OUTPUTF="mkv"
		else
			DEFAULT_OUTPUTF="m4v"
		fi
	fi
}

function crop {
	if [ "$(which mplayer)" != "" ]; then
		SOURCE="$DEFAULT_PATH"
		CROP="1"
		TOTAL_LOOPS="10"
		NICE_PRI="10"
		VF_OPTS="pp=lb,"
		A=0
  		while [ "$A" -lt "$TOTAL_LOOPS" ] ; do
    		A="$(( $A + 1 ))"
    		SKIP_SECS="$(( 35 * $A ))"
    		log=$(nice -n $NICE_PRI nohup mplayer "$SOURCE" $CHAPTER -ss $SKIP_SECS -identify -frames 20 -vo md5sum -ao null -nocache -quiet -vf ${VF_OPTS}cropdetect=20:16 2>&1 > mplayer.log < /dev/null)
    		CROP[$A]=`awk -F 'crop=' '/crop/ {print $2}' < mplayer.log| awk -F ')' '{print $1}' |tail -n 1`
    	done
    	rm md5sums mplayer.log
    	
    	B=0
    	while [ "$B" -lt "$TOTAL_LOOPS" ] ; do
			B="$(( $B + 1 ))"
  			C=0
			while [ "$C" -lt "$TOTAL_LOOPS" ] ; do
				C="$(( $C + 1 ))"
  
				if [ "${CROP[$B]}" == "${CROP[$C]}" ] ; then
					COUNT_CROP[$B]="$(( ${COUNT_CROP[$B]} + 1 ))"
				fi
			done  
		done
		
		HIGHEST_COUNT=0
		D=0
		while [ "$D" -lt "$TOTAL_LOOPS" ] ; do
			D="$(( $D + 1 ))"
  
			if [ "${COUNT_CROP[$D]}" -gt "$HIGHEST_COUNT" ] ; then
				HIGHEST_COUNT="${COUNT_CROP[$D]}"
				GREATEST="$D"
			fi
		done
		echo $(echo "-filter:v crop=${CROP[$GREATEST]}")    	
	fi
}

function checkAvailableSpace {
	
	kb=`df -kP "$dictPath" | tail -1 | awk '{print $4}'`
	ob=`wc -c "$DEFAULT_PATH" |tail -1 |awk '{print $1}'`
	
	#Size in GB
	kbg=$(echo "$kb/1024/1024"|bc)
	obg=$(echo "($ob/1024/1024/1024)+1"|bc)
	
	if [ "$kbg" -lt "$obg" ]; then
		#Not enough space.
		f_ERROR "Insufficient Disk Space ($kbg GB left)."
		clear
		echo -e "Insufficient Disk Space ($kbg GB left).\n\nPlease move some files, the script will refresh the available disk space every 60s."
		
		sleep 60
		checkAvailableSpace
	fi
}

function startEncode {
	checkSize "$DEFAULT_PATH"
	checkAvailableSpace
	
	rm -f /tmp/vstats*
	fullfile=`basename "$DEFAULT_PATH"`
	filename="${fullfile%.*}"
	
	fiCod=$(checkFileCodecs)
	
	if [[ "$fiCod" != *c:v:?\ copy* ]];
	then
		#No video stream copy detected, need to check crop value.
		cropVal=$(crop)
		f_INFO "Cropping Video to: $(echo $cropVal|sed 's/-filter:v crop=//g')"
	fi
	
	trap "exit 1" SIGINT SIGTERM
	
	f_INFO "ffmpeg-command:\n\nffmpeg -y -sub_charenc UTF-8 -vstats_file /tmp/vstats -i \"$DEFAULT_PATH\" $fiCod $cropVal \"$dictPath/output/$filename.$DEFAULT_OUTPUTF\"\n"
	
	#exit 0
	
	nice -n 15 ffmpeg -y -vstats_file /tmp/vstats -i "$DEFAULT_PATH" $fiCod $cropVal "$dictPath/output/$filename.$DEFAULT_OUTPUTF" 2>/dev/null & 
        PID=$! && 
	showFrame "$PID" $(echo "$cropVal"|sed 's/-filter:v crop=//g')
	
	checkSanity
	
	rm -f /tmp/vstats*
	dictProgress=`echo "$dictProgress+1"|bc`
	f_INFO "Encoding for $DEFAULT_PATH done."
}

f_INFO "Started 'Convert with Pacman'."
performEncode
