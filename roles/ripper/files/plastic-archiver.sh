#!/usr/bin/env bash

export PATH="$PATH:$PWD"

. log4bash.sh
log4bash_timefmt="+%Y-%m-%dT%H:%M:%S%z"

# Default configuration
CAPTURE_BASEDIR=.
CAPTURE_ID=$(uuidgen)

usage() { echo "Usage: $0 [-i <CAPTURE_ID>] [-o <capture_basedir>] <reader_device>" 1>&2; exit 1; }

while getopts ":i:o:R" o; do
    case "${o}" in
        o)
            CAPTURE_BASEDIR="$OPTARG"
            ;;
        i)
            CAPTURE_ID="$OPTARG"
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

readonly cdrdao_tocfile=toc.txt
readonly cdrdao_datafile=data.bin

run_cdrdao() {
    if ! cdrdao read-cd --device "$reader_device" --datafile "$cdrdao_datafile" "$cdrdao_tocfile"; then
        log_warning "Disk could not be read normally (usually due to L-EC errors), attemptin raw read instead"
        rm -f "$cdrdao_tocfile" "$cdrdao_datafile"
        cdrdao read-cd --device "$reader_device" --datafile "$cdrdao_datafile" --read-raw "$cdrdao_tocfile" || exit $?
    fi
}

case $disk_type in
    no-disc)
        log_error "Disk not detected"
        exit 1
        ;;
    audio-cd|type-1-data)
        pushd contents 2> /dev/null
        run_cdrdao
        popd
        ;;
    *)
        log_error "Unknown disk type '$disk_type'"
        ;;

esac

popd
