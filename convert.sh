#!/bin/bash
DEFAULT_PATH=""
dictPath="$(pwd)"
searchExt="avi|flv|iso|mov|mp4|mpeg|mpg|ogg|ogm|ogv|wmv|m2ts|rmvb|rm|3gp|m4a|3g2|mj2|asf|divx|vob|mkv"
crfVal="18.0"

dictTotal=1
dictProgress=0
DEFAULT_OUTPUTF=""

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
	
	if [ "$1" = "0" ]; then
		count=0
		for ai in  `mediainfo --Inform="Audio;%ID%:%Language/String%:%Format%:%Channels%\n" "$DEFAULT_PATH"| cut -d' ' -f1`
		do
			count=`echo "$count+1" |bc`
		done
		echo "$count"
	else
		for ai in  `mediainfo --Inform="Audio;%ID%:%Language/String%:%Format%:%Channels%\n" "$DEFAULT_PATH"| cut -d' ' -f1`
		do
			if [ $(echo $ai|cut -d':' -f1) = "$1" ]; then
				echo "$ai"
			fi
		done
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
		if [ "${x:0:3}" = "crf" ];
		then 
			#CRF of Video
			crf=${x:4:6}; 
		fi
	done
	
	echo ${crf/./}
}

function checkFileCodecs {
	numberOfTracks=`echo "$(getAudioInfo 0)+1" |bc`
	
	returnMap="-loglevel panic -stats -map 0:0"
	#returnMap="-stats -map 0:0"
	#returnFlag="-c:v:0 copy"
	
	if [ $(printf "%d\n" $(getVidQuality)) -gt $(printf "%d\n" ${crfVal/./}) ]; then 
		#Vid Quality is lower than expected no need to reencode.
		returnFlag="-c:v:0 copy"
	else
		returnFlag="-c:v:0 libx264 -profile:v high -level 4.1 -preset slow -crf $crfVal -tune film"
	fi
	counter=0
	
	for (( i=0;i<=numberOfTracks;i++ ))
	do
		
		if [[ "$(getAudioCodec $i)" = "AAC" && "$DEFAULT_OUTPUTF" = "m4v" ]]; then
			#Found AAC-Codec, check for AC3 with same language
			doubleLang=false
			aacLang="$(getAudioLanguage $i)"
			
			for (( j=0;j<=numberOfTracks;j++ ));
			do
				if [[ "$(getAudioLanguage $j)" = "$aacLang" &&  "$(getAudioCodec $j)" = "AC-3" ]]; then
					doubleLang=true;
				fi
			done
			
			if [ $doubleLang = false ]; then
				#Copy this track and add AC3 with same channel amount
				#echo "AAC Track found"
				currPos=`echo "$i-1"|bc`
				returnMap="$returnMap -map 0:$currPos -map 0:$currPos"
				returnFlag="$returnFlag -c:a:$counter copy"
				counter=`echo "$counter+1"|bc`
				returnFlag="$returnFlag -c:a:$counter ac3 -b:a:$counter 640k -ac:"$(echo "$counter+1"|bc)" $(getAudioChannels $i)"
				counter=`echo "$counter+1"|bc`
			else
				returnMap="$returnMap -map 0:$i"
				returnFlag="$returnFlag -c:a:$counter copy"
				counter=`echo "$counter+1"|bc`
			fi
		elif [[ "$(getAudioCodec $i)" = "AC-3" && "$DEFAULT_OUTPUTF" = "m4v" ]]; then
			#Found AC3-Codec, check for AAC with same language
			doubleLang=false;
			ac3Lang="$(getAudioLanguage $i)"
			for (( j=0;j<=numberOfTracks;j++ )) do
				if [[ "$(getAudioLanguage $j)" = "$ac3Lang"  &&  "$(getAudioCodec $j)" = "AAC" ]]; then
					doubleLang=true;
				fi
			done
			
			if [ $doubleLang = false ]; then
				#Copy this track and add 2-Channel-AAC in front!
				#echo "AC-3 Track found"
				currPos=`echo "$i-1"|bc`
				returnMap="$returnMap -map 0:$currPos -map 0:$currPos"
				returnFlag="$returnFlag -c:a:$counter libfaac -b:a:$counter 320k -ac:"$(echo "$counter+1"|bc)" 2"
				counter=`echo "$counter+1"|bc`
				returnFlag="$returnFlag -c:a:$counter copy"
				counter=`echo "$counter+1"|bc`
			else
				returnMap="$returnMap -map 0:$i"
				returnFlag="$returnFlag -c:a:$counter copy"
				counter=`echo "$counter+1"|bc`
			fi
		elif [[ "$(getAudioCodec $i)" = "DTS" && "$DEFAULT_OUTPUTF" = "m4v" ]]; then
			#Mux that shit to ac3 aac
			
			currPos=`echo "$i-1"|bc`
			returnMap="$returnMap -map 0:$currPos -map 0:$currPos"
			returnFlag="$returnFlag -c:a:$counter libfaac -b:a:$counter 320k -ac:"$(echo "$counter+1"|bc)" 2"
			counter=`echo "$counter+1"|bc`
			returnFlag="$returnFlag -c:a:$counter ac3 -b:a:$counter 640k -ac:"$(echo "$counter+1"|bc)" $(getAudioChannels $i)"
			counter=`echo "$counter+1"|bc`
		elif [ "$DEFAULT_OUTPUTF" = "mkv" ]; then
			i=`echo "$i+1"|bc`
			currPos=`echo "$counter+1"|bc`
			returnMap="$returnMap -map 0:$currPos"
			returnFlag="$returnFlag -c:a:$counter copy"
			counter=`echo "$counter+1"|bc`
		fi
	done
	echo "$returnMap $returnFlag"
}

function parseArguments {
	echo "Argh"
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
	echo -e "#    Pacman-Convert:\tVersion 0.3\t\t(built on May 12 2014)"
	echo -e "#    ffmpeg:\t\tVersion $(ffmpeg -version |head -n1 |cut -d' ' -f3)\t\t($(ffmpeg -version |sed -n 2p|cut -d'w' -f1| awk '{$1=$1}1'|sed 's/.\{9\}$//'))"
	echo -e "#    x264:\t\tVersion $(x264 --version|head -n1| cut -d' ' -f2)\t($(x264 --version |sed -n 2p|cut -d',' -f1| awk '{$1=$1}1'))"

	echo -e "#"
	echo -e "#  Progress:"
	echo -e "#    File #:\t\t"$(($dictProgress+1))"/$dictTotal"
	echo -e "#    Filename:\t\t$(getFilename true)"
	echo -e "#    Resolution:\t$(echo $2|cut -d':' -f1)x$(echo $2|cut -d':' -f2)"
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
		
		if [ $leDif -lt 30 ]; then
			#Differs by max. thirty Seconds... Okay delete Original.
			rm "$DEFAULT_PATH"
		fi
	fi

}

function calculateTotalVideos {
	dictTotal=`find -E "$dictPath" -follow -regex '.*\.('$searchExt')'|wc -l|sed 's/[^0-9]*//g'`
}

function performEncode {
	mkdir -p "$dictPath/output"
		calculateTotalVideos
		find -E "$dictPath" -follow -regex '.*\.('$searchExt')' -print0 | while IFS= read -r -d $'\0' line; do
			if [ $(dirname "$line") != "$dictPath/output" ]; then
				startEncode "$line"
			fi
		done
}

function checkSize {
	filesize=$(wc -c "$1"|cut -d' ' -f2|sed 's/[^0-9]*//g')
	
	if [[ $(printf "%.0f" $filesize) -gt 7516192768 && "$DEFAULT_OUTPUTF" = "" ]]
	then
		DEFAULT_OUTPUTF="mkv"
	else
		DEFAULT_OUTPUTF="m4v"
	fi
}


function cropDetect
{
 		echo $(ffmpeg -i "$@" -t 1 -vf cropdetect -f null - 2>&1 | awk '/crop/ { print $NF }' | tail -1|sed 's/crop=//g' )
}

function startEncode {
	DEFAULT_PATH="$1"
	checkSize "$1"

	rm -f /tmp/vstats*
	fullfile=`basename "$1"`
	filename="${fullfile%.*}"
	
	cropFrame=$(cropDetect "$1")
	
	echo $(checkFileCodecs)
	exit 0
	
	nice -n 15 ffmpeg -y -vstats_file /tmp/vstats -i "$1" $(checkFileCodecs) -filter:v crop=$cropFrame "$dictPath/output/$filename.$DEFAULT_OUTPUTF" 2>/dev/null & 
        PID=$! && 
	showFrame "$PID" "$cropFrame"

	
	checkSanity
	
	rm -f /tmp/vstats*
	dictProgress=`echo "$dictProgress+1"|bc`
}

performEncode