#!/bin/sh

while [ "$1" ]; do
    filename="$1"; shift
    chdkptp.sh -c -erec -e"remoteshoot $filename"
done
