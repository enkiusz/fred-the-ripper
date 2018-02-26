set xlabel "Size [MB]"
set ylabel "Rip time [min]"

#
# Example gnuplot parameters:
#
# gnuplot -p -e 'datastream="cat /mnt/tank/cd-dumps/production-run-*/summary.dat"' summary-plot.gnuplot
#

plot '<'.datastream.'| grep -F audio-cd' using ($4/1000000):($7/60) with points title 'audio-cd', '<'.datastream.'| grep -F type-1-data' using ($4/1000000):($7/60) with points title 'type-1-data'

