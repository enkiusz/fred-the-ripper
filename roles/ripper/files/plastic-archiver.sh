#!/usr/bin/env bash

export PATH="$PATH:$PWD"

. log4bash.sh
log4bash_timefmt="+%Y-%m-%dT%H:%M:%S%z"

# Default configuration
CAPTURE_BASEDIR=.
CAPTURE_ID=$(uuidgen)
unset RAW_RAW_FIGHT_THE_POWAH

usage() { echo "Usage: $0 [-i <CAPTURE_ID>] [-o <capture_basedir>] [-R] <reader_device>" 1>&2; exit 1; }

while getopts ":i:o:R" o; do
    case "${o}" in
        o)
            CAPTURE_BASEDIR="$OPTARG"
            ;;
        i)
            CAPTURE_ID="$OPTARG"
            ;;
        R)
            RAW_RAW_FIGHT_THE_POWAH=true
            ;;
        *)
            usage
            ;;
    esac
done
shift $((OPTIND-1))

reader_device="$1"; shift
if [ -z "$reader_device" ]; then
    usage
fi

context_push "id='$CAPTURE_ID'"
context_push "dev='$reader_device'"
export CDROM="$reader_device" # Export env for cdctl command (see man cdctl)

capture_dir="$CAPTURE_BASEDIR/$CAPTURE_ID"
mkdir -p "$capture_dir"; pushd "$capture_dir" 2> /dev/null

# Empty metadata file just to mark that spec v0 is being used,
# in later versions this file may contain other info.
touch metadata-v0

mkdir "reader"
lsblk -O -J "$reader_device" | jq ' .blockdevices | .[0]' > reader/reader.json
cdrdao drive-info --device "$reader_device" > reader/mmc-drive-info.txt

log_info "Storing info to '$capture_dir'"

disk_type=$(cdctl -g |
                sed -e 's|There is no CD/DVD in the drive (no disc)\.|no-disc|' \
                    -e 's|There is an audio CD/DVD in the drive.|audio-cd|' \
                    -e 's|There is a type 1 data CD/DVD in the drive.|type-1-data|' \
                    )

log_debug "Detected disk type is '$disk_type'"
echo "$disk_type" > disk-type.txt

# Read RAW TOC in hex
readom "dev=$reader_device" -fulltoc 2>&1 | grep -E "^[0-9A-Fa-f ]+" > toc.hex

# Disk info
disk_info="$(cdrdao disk-info --device "$reader_device")"
echo "$disk_info" > disk-info.txt

session_count=$(echo "$disk_info" | grep Sessions | awk '{print $3;}')
# Maybe read raw hex TOC and store it too?
# Or maybe read TOC file using cdrdao, it seems to read and store much more information

toc=$(cdctl --list)
echo "$toc" > toc.txt
log_info "Disc contains $session_count session(s), TOC has $(echo "$toc" | grep -F audio | wc -l) audio tracks + $(echo "$toc" | grep -F data | wc -l) data tracks ($(echo "$toc" | wc -l) tracks total)"

if [ $session_count -gt 1 ]; then
    # This is a multisession cd
    log_error "Multisession disks are not yet supported"
    exit 1
fi

mkdir contents


case $disk_type in
    no-disc)
        log_error "Disk not detected"
        exit 1
        ;;
    audio-cd)
        mcn=$(cdctl -m)
        echo "$mcn" > mcn.txt

        log_debug "Disk MCN/UPC is '$mcn'"
        pushd contents 2> /dev/null

        # cdrdao or cdparanoia???
        cdrdao read-cd --device "$reader_device" ${RAW_RAW_FIGHT_THE_POWAH:+--read-raw} toc.txt

        # if [ -x $(which cdparanoia) ]; then
        #     cdparanoia -Q > cdparanoia-toc.txt 2>&1 
        #     cdparanoia -d "$reader_device" -l 

        #     # Needs more info for audioCD support
        #     # abcde?
        #     # https://bbs.archlinux.org/viewtopic.php?id=32471
        #     # https://www.mail-archive.com/flac@xiph.org/msg00040.html

        #     #
        #     # cdrdao to read TOC, convert to cue file without mkcue
        #     # cdparanoia or cdrdao to read cd
        #     # maybe abcde to read as single FLAC
        # fi

        popd

        ;;
    type-1-data)
        pushd contents 2> /dev/null
        # Should we use --read-raw???
        cdrdao read-cd --device "$reader_device" ${RAW_RAW_FIGHT_THE_POWAH:+--read-raw} toc.txt
        popd
        ;;
    *)
        log_error "Unknown disk type '$disk_type'"
        ;;

esac

popd

