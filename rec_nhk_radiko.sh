#!/bin/bash
# https://gist.github.com/riocampos/93739197ab7c765d16004cd4164dca73

DATE=`date '+%Y%m%d'`

if [ $# -eq 2 ]; then
  CHANNEL="$1"
  DURATION=`expr $2 \* 60`
  OUTDIR="."
elif [ $# -eq 3 ]; then
  CHANNEL="$1"
  DURATION=`expr $2 \* 60`
  OUTDIR="$3" 
else echo "usage : $0 channel_name(r1|r2|fm) duration(minuites) [outputdir]"
  exit 1
fi

case $CHANNEL in
    r1) M3U8URL='https://nhkradioakr1-i.akamaihd.net/hls/live/511633/1-r1/1-r1-01.m3u8' ;;
    r2) M3U8URL='https://nhkradioakr2-i.akamaihd.net/hls/live/511929/1-r2/1-r2-01.m3u8' ;;
    fm) M3U8URL='https://nhkradioakfm-i.akamaihd.net/hls/live/512290/1-fm/1-fm-01.m3u8' ;;
    *) exit 1 ;;
esac

d=$(basename ${OUTDIR})
/usr/bin/avconv -i ${M3U8URL} -write_xing 0 -t ${DURATION} "${OUTDIR}/${d}_${DATE}.mp3"

if [ $? = 0 ]; then
  rm -f "/tmp/${CHANNEL}_${DATE}"
fi

