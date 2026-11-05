set -e
N=1008
for k in 0 1 2; do A=$((k*336)); B=$(((k+1)*336)); RANGE=$A,$B node rend.js index.html part$k.mp4 24 > log$k.txt 2>&1 & done
wait
printf "file part0.mp4\nfile part1.mp4\nfile part2.mp4\n" > parts.txt
ffmpeg -y -loglevel error -f concat -i parts.txt -c copy aviary_silent.mp4
echo DONE
