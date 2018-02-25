#!/bin/sh

video_device="$1"; shift
path="$1"; shift

while true; do
    ts=$(date --utc +%Y-%m-%dT%H:%M:%SZ)
    video_file="$path/debug-$ts.mkv"

    echo "Starting to record from device '$video_device' to '$video_file'"

    ffmpeg -f v4l2 -nostats -framerate 10 -video_size 320x240 -i "$video_device" -timestamp now "$video_file"

    sleep 1
done
