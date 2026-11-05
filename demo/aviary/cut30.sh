# 30-second cut from the 42 s master (aviary_full.mp4): six shots joined with 0.3 s dissolves
set -e
IN=aviary_full.mp4; OUT=aviary_30s.mp4; X=0.3
SEG=("0 7.5" "8.6 13.6" "15.0 19.5" "24.0 27.0" "29.2 33.2" "35.0 42.0")
F=""; i=0
for s in "${SEG[@]}"; do set -- $s; F="$F[0:v]trim=$1:$2,setpts=PTS-STARTPTS[v$i];[0:a]atrim=$1:$2,asetpts=PTS-STARTPTS[a$i];"; i=$((i+1)); done
off=0; prev=v0; preva=a0; len=7.5
for k in 1 2 3 4 5; do set -- ${SEG[$k]}; d=$(python3 -c "print($2-$1)"); off=$(python3 -c "print($len-$X)"); F="$F[$prev][v$k]xfade=transition=fade:duration=$X:offset=$off[x$k];[$preva][a$k]acrossfade=d=$X[y$k];"; prev=x$k; preva=y$k; len=$(python3 -c "print($len+$d-$X)"); done
ffmpeg -y -loglevel error -i $IN -filter_complex "${F%;}" -map "[$prev]" -map "[$preva]" -c:v libx264 -crf 20 -preset medium -pix_fmt yuv420p -c:a aac -b:a 192k -movflags +faststart $OUT
echo "len $len"
