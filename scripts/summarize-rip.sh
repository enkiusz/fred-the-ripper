#!/bin/sh

date2stamp () {
    date --utc --date "$1" +%s
}

echo -e "#ID\tdisk_type\tsize\telapsed"

while [ "$1" ]; do
    dir="$1"; shift
    id=$(basename "$dir")
    echo "Summarizing rip to dir '$dir'" >&2 

    log_file="$dir/log.txt"
    if [ ! -r "$log_file" ]; then
        echo "Rip $id is still ongoing, skipping directory" >&2
        continue
    fi

    end_ts=$(tail -n 1 < "$log_file" | awk '{print $1;}')
    begin_ts=$(head -n 2 < "$log_file" | tail -n 1 | awk '{print $1;}')
    elapsed=$(( $(date2stamp $end_ts) - $(date2stamp $begin_ts) ))

    size=$(stat -c %s $dir/contents/data.bin)
    disk_type=$(cat $dir/disk-type.txt)

    echo "Rip $id disktype='$disk_type' begin='$begin_ts' end='$end_ts' elapsed='$elapsed' seconds datasize='$size' bytes " >&2
    echo -e "$id\t$disk_type\t$size\t$elapsed"
done
