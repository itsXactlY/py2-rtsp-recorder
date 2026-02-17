#!/bin/sh
# Simple Watchdog for the RTSP Recorder
# Add to /etc/rc.local for autostart

# Pfad anpassen!
cd /mnt/pools/A/A0/IP-Cam

echo "Starting RTSP Recorder Watchdog..."

while true; do
    # Log rotation (keep log small)
    if [ -f service.log ] && [ $(stat -c%s service.log) -gt 1048576 ]; then
        mv service.log service.log.old
    fi

    echo "[$(date)] Starting python script..." >> service.log
    
    # Start script
    python src/record.py >> service.log 2>&1
    
    echo "[$(date)] Script crashed/exited. Restarting in 10s..." >> service.log
    sleep 10
done
