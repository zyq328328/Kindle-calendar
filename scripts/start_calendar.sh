#!/bin/bash
# Start Kindle Calendar - stop cvm, run app, restart cvm on exit

# Stop cvm so our app can be foreground and receive touch events
killall -STOP cvm 2>/dev/null

# Clean up any old processes
killall -9 python3 2>/dev/null
sleep 1

# Run our app
cd /mnt/us/calendar
python3 -u main.py
APP_EXIT=$?

# Restart cvm
killall -CONT cvm 2>/dev/null

exit $APP_EXIT