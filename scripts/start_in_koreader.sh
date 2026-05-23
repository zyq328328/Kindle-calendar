#!/bin/bash
# Start calendar app in KOReader mode
# This script should be run AFTER KOReader has stopped cvm

# Wait for cvm to be fully stopped
sleep 1

# Create FIFO for input events
rm -f /tmp/cal_input.fifo
mkfifo /tmp/cal_input.fifo

# Start our Python app, reading from the FIFO
cd /mnt/us/calendar

# Our app reads from stdin or named pipe
python3 -u main.py < /tmp/cal_input.fifo &

# Copy input events to FIFO
cat /dev/input/event1 > /tmp/cal_input.fifo &

echo "Calendar app started"