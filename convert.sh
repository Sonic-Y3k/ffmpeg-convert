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
	
	
	if [ "$1" = "-1" ]; then
		count=0
		
		for vI in  `mediainfo --Inform="Video;%ID%:%Language/String%:%Format%:%Channels%\n" "$DEFAULT_PATH"| cut -d' ' -f1`
		do
			count=`echo "$count+1" |bc`
		done
		
		for aI in  `mediainfo --Inform="Audio;%ID%:%Language/String%:%Format%:%Channels%\n" "$DEFAULT_PATH"| cut -d' ' -f1`
		do
			count=`echo "$count+1" |bc`
		done
		
		for tI in  `mediainfo --Inform="Text;%ID%:%Language/String%:%Format%:%Channels%\n" "$DEFAULT_PATH"| cut -d' ' -f1`
		do
			count=`echo "$count+1" |bc`
		done
		echo "$count"
	else
		ret=""
		for vI in  `mediainfo --Inform="Video;%ID%:Unknown:%Format%:Unknown\n" "$DEFAULT_PATH"| cut -d' ' -f1`
		do
			if [ $(echo $vI|cut -d':' -f1) = "$1" ]; then
				ret="$vI"
			fi
		done	
		for aI in  `mediainfo --Inform="Audio;%ID%:%Language/String%:%Format%:%Channels%\n" "$DEFAULT_PATH"| cut -d' ' -f1`
		do
			if [ $(echo $aI|cut -d':' -f1) = "$1" ]; then
				ret="$aI"
			fi
		done
		for tI in  `mediainfo --Inform="Text;%ID%:%Language/String%:%Format%:%Channels%\n" "$DEFAULT_PATH"| cut -d' ' -f1`
		do
			if [ $(echo $tI|cut -d':' -f1) = "$1" ]; then
				ret="$tI"
			fi
		done
		
		if [ "$ret" == "" ]; then
			echo "Unknown"
		else
			echo "$ret"
		fi
		
	fi
}

function getAudioLanguage {
	if [ -z "$1" ]; then
		#You need to specify a Track#
		exit 0
	fi
	echo $(echo $(getAudioInfo $1)|cut -d':' -f2)
	
}

function getAudioCodec {
	if [ -z "$1" ]; then
		#You need to specify a Track#
		exit 0
	fi
	
	echo $(echo $(getAudioInfo $1)|cut -d':' -f3)
}

function getAudioChannels {
	if [ -z "$1" ]; then
		#You need to specify a Track#
		exit 0
	fi
	echo $(echo $(getAudioInfo $1)|cut -d':' -f4)
	
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

function checkFileCodecs {
	returnMap="-loglevel panic -stats"
	subCount=0
	audCount=0
	newCount=0
	
	numberOfTracks=`echo "$(getAudioInfo -1)" |bc`

	f_INFO "Analyze $numberOfTracks Tracks:"
	for (( i=0;i<=numberOfTracks;i++ ))
	do
		currCod="$(getAudioCodec $i)"
		#Video
		if [[ "$currCod" == "AVC" || "$currCod" == "AVI" || "$currCod" == "MPEG-4" ]]; then
			
			if [ $i -eq 0 ]; then
				tempInc="+1"
			fi
			if [ $(printf "%d\n" $(getVidQuality)) -ge $(printf "%d\n" ${crfVal/./}) ]; then 
			#Vid Quality is lower than expected no need to reencode.
				returnMap="$returnMap -map 0:$(echo $i-1$tempInc|bc)"
				returnFlag="-c:v:0 copy"
				f_INFO "-Stream #0:$i ($currCod) -> #0:$newCount (copy)"
				newCount=$(echo "$newCount+1"|bc)
			else
				returnMap="$returnMap -map 0:$(echo $i-1$tempInc|bc)"
				returnFlag="-c:v:0 libx264 -profile:v high -level 4.1 -preset slow -crf $crfVal -tune film"
				f_INFO "-Stream #0:$i ($currCod) -> #0:$newCount (libx264)"
				newCount=$(echo "$newCount+1"|bc)
			fi
		
		#Audio
		elif [[ "$DEFAULT_OUTPUTF" == "mkv" && ( "$currCod" = "DTS" || "$currCod" = "AC-3" ) ]]; then
			returnMap="$returnMap -map 0:$(echo $i-1$tempInc|bc)"
			returnFlag="$returnFlag -c:a:$audCount copy"
			audCount=$(echo "$audCount+1"|bc)
			f_INFO "-Stream #0:$i ($currCod) -> #0:$newCount (copy)"
			newCount=$(echo "$newCount+1"|bc)
		elif [[ "$DEFAULT_OUTPUTF" == "m4v" && "$currCod" == "AC-3" ]]; then
		#Found AC3-Codec, check for AAC with same language
			doubleLang=false;
			ac3Lang="$(getAudioLanguage $i)"
			for (( j=0;j<=numberOfTracks;j++ )) do
				if [[ "$(getAudioLanguage $j)" = "$ac3Lang"  &&  "$(getAudioCodec $j)" = "AAC" ]]; then
					doubleLang=true;
				fi
			done
			
			if [ $doubleLang = false ]; then
				returnMap="$returnMap -map 0:$(echo $i-1$tempInc|bc) -map 0:$(echo $i-1|bc)"
				returnFlag="$returnFlag -c:a:$audCount libfaac -b:a:$audCount 320k -ac:"$(echo "$audCount+1"|bc)" 2"
				f_INFO "-Stream #0:$i ($currCod) -> #0:$newCount (libfaac)"
				newCount=$(echo "$newCount+1"|bc)
				audCount=$(echo "$audCount+1"|bc)
				returnFlag="$returnFlag -c:a:$audCount copy"
				f_INFO "-Stream #0:$i ($currCod) -> #0:$newCount (copy)"
				audCount=$(echo "$audCount+1"|bc)
				newCount=$(echo "$newCount+1"|bc)
				
			else
				returnMap="$returnMap -map 0:$(echo $i-1$tempInc|bc)"
				returnFlag="$returnFlag -c:a:$audCount copy"
				f_INFO "-Stream #0:$i ($currCod) -> #0:$newCount (copy)"
				audCount=$(echo "$audCount+1"|bc)
				newCount=$(echo "$newCount+1"|bc)
			fi
		elif [[ "$DEFAULT_OUTPUTF" = "m4v" && ("$currCod" = "DTS" || "$currCod" = "MP3" || "$currCod" = "MPEG" ) ]]; then
			returnMap="$returnMap -map 0:$(echo $i-1$tempInc|bc) -map 0:$(echo $i-1$tempInc|bc)"
			returnFlag="$returnFlag -c:a:$audCount libfaac -b:a:$audCount 320k -ac:"$(echo "$audCount+1"|bc)" 2"
			f_INFO "-Stream #0:$i ($currCod) -> #0:$newCount (libfaac)"
			newCount=$(echo "$newCount+1"|bc)
			audCount=$(echo "$audCount+1"|bc)
			audChannels=$(getAudioChannels $i)
			returnFlag="$returnFlag -c:a:$audCount ac3 -b:a:$audCount 640k -ac:"$(echo "$audCount+1"|bc)" "$((audChannels>1?audChannels:2))" "
			f_INFO "-Stream #0:$i ($currCod) -> #0:$newCount (ac3)"
			newCount=$(echo "$newCount+1"|bc)
			audCount=$(echo "$audCount+1"|bc)
		elif [[ "$DEFAULT_OUTPUTF" == "m4v" && "$currCod" == "AAC" ]]; then
		#Found AAC-Codec, check for AC3 with same language
			doubleLang=false;
			ac3Lang="$(getAudioLanguage $i)"
			for (( j=0;j<=numberOfTracks;j++ )) do
				if [[ "$(getAudioLanguage $j)" = "$ac3Lang"  &&  "$(getAudioCodec $j)" = "AC-3" ]]; then
					doubleLang=true;
				fi
			done
			
			if [ $doubleLang = false ]; then
				returnMap="$returnMap -map 0:$(echo $i-1$tempInc|bc) -map 0:$(echo $i-1|bc)"
				returnFlag="$returnFlag -c:a:$audCount copy"
				f_INFO "-Stream #0:$i ($currCod) -> #0:$newCount (copy)"
				newCount=$(echo "$newCount+1"|bc)
				audCount=$(echo "$audCount+1"|bc)
				returnFlag="$returnFlag -c:a:$audCount ac3 -b:a:$audCount 640k -ac:$audCount $(getAudioChannels $i)"
				f_INFO "-Stream #0:$i ($currCod) -> #0:$newCount (ac3)"
				newCount=$(echo "$newCount+1"|bc)
				audCount=$(echo "$audCount+1"|bc)
			else
				returnMap="$returnMap -map 0:$(echo $i-1$tempInc|bc)"
				returnFlag="$returnFlag -c:a:$audCount copy"
				f_INFO "-Stream #0:$i ($currCod) -> #0:$newCount (copy)"
				newCount=$(echo "$newCount+1"|bc)
				audCount=$(echo "$audCount+1"|bc)
			fi
			
		#Subtitles
		elif [[ "$DEFAULT_OUTPUTF" = "mkv" && ( "$currCod" = "PGS" || "$currCod" = "VobSub" || "$currCod" = "UTF-8" ) ]]; then
			returnMap="$returnMap -map 0:$(echo $i-1$tempInc|bc)"
			returnFlag="$returnFlag -c:s:$subCount copy"
			f_INFO "-Stream #0:$i ($currCod) -> #0:$newCount (copy)"
			newCount=$(echo "$newCount+1"|bc)
			subCount=$(echo "$subCount+1"|bc)
		elif [[ "$DEFAULT_OUTPUTF" = "m4v" && ( "$currCod" = "PGS" || "$currCod" = "UTF-8" || "$currCod" = "MOV" || "$currCod" = "mov_text" || "$currCod" = "text" ) ]]; then
			returnMap="$returnMap -map 0:$(echo $i-1$tempInc|bc)"
			returnFlag="$returnFlag -c:s:$subCount mov_text"
			f_INFO "-Stream #0:$i ($currCod) -> #0:$newCount (mov_text)"
			newCount=$(echo "$newCount+1"|bc)
			subCount=$(echo "$subCount+1"|bc)	
		fi
	done
	echo "$returnMap $returnFlag"
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
	echo -e "#    Pacman-Convert:\tVersion 1.2\t\t(built on Jul 02 2014)"
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
			f_INFO "Passed sanity check. Deleting original video."
		else
			f_WARNING "Failed sanity check (diff $leOne, $leTwo = $leDif < 250). Keep all files."
		fi
	fi

}

function calculateTotalVideos {
	dictTotal=`find -E "$dictPath" -follow -regex '.*\.('$searchExt')' 2>&1|grep -v 'Permission denied'|grep -v '/output/'|wc -l|sed 's/[^0-9]*//g'`
}

function performEncode {
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
										
	if [[ $(printf "%.0f" $filesize) -gt 5368709120 && "$DEFAULT_OUTPUTF" = "" ]]
	then
		DEFAULT_OUTPUTF="mkv"
	else
		DEFAULT_OUTPUTF="m4v"
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
	
	f_INFO "ffmpeg-command:\n\nffmpeg -y -vstats_file /tmp/vstats -i \"$DEFAULT_PATH\" $fiCod $cropVal \"$dictPath/output/$filename.$DEFAULT_OUTPUTF\"\n"
	
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
