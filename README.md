# Py2-RTSP-Recorder 📹💾

A lightweight, ultra-robust RTSP video recorder designed for **legacy hardware**, **NAS systems**, and **embedded devices** running Python 2.7.

It connects to an IP camera via RTSP, authenticates (supporting Digest/Basic), extracts the raw H.264 stream, and saves it to disk with **zero transcoding**.

> **Why?** Because modern tools like `ffmpeg` or `OpenCV` are often too heavy, incompatible, or impossible to compile on old ARM/MIPS kernels (e.g., Linux 2.6). This script uses standard libraries only and runs on <5% CPU. (<2% on ARMV5 - 990MHz Feroceon 88FR131 rev 1)

---

## Features

- 🐍 **Pure Python 2**  
  No external libraries required. Uses only standard modules: `socket`, `hashlib`, `os`.

- 🚀 **Zero-Copy Performance**  
  Writes raw H.264 NAL units directly to disk.

- 📂 **Smart Rotation**  
  Creates hourly segments organized by:
  ```
  YYYY-MM/DD/HH-MM.h264
  ```

- 🧹 **Auto-Cleanup**  
  Automatically monitors disk usage and deletes recordings older than X days.

- 🛡️ **Robustness**
  - Handles network drops and camera reboots
  - Reassembles FU-A fragmented H.264 packets (essential for playback)
  - Injects Start Codes (`00 00 00 01`) for compatibility with VLC/MPV
  - Includes a "watchdog" script for 24/7 uptime

---

## Requirements

- Python 2.x (Tested on 2.5)
- A network camera with RTSP support (H.264 video)
- Sufficient storage space for recordings

---

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/itsXactlY/py2-rtsp-recorder.git
cd py2-rtsp-recorder
```

### 2. Create Credentials File

Create a file named `creds.txt` inside the project folder.

It must contain:

```
admin
mysecretpassword
```

- Line 1 → Username  
- Line 2 → Password  

### 3. Configuration

Open `src/record.py` and adjust the configuration variables at the top:

```python
# --- CONFIGURATION ---
CRED_FILE = '/mnt/pools/A/A0/IP-Cam/creds.txt'
HOST = '192.168.0.225'       # Camera IP
PORT = 554
STREAM_URI = '/stream1'      # RTSP Stream Path
DEST = '/mnt/pools/A/A0/IP-Cam/recordings'
RETENTION_DAYS = 14          # Delete files older than 14 days
```

---

## Usage

### Manual Start

To test the connection and start recording:

```bash
python src/record.py
```

Press `Ctrl+C` to stop.

### 24/7 Background Service (Watchdog)

To ensure the recorder runs continuously and restarts automatically after crashes or reboots, use the provided shell script.

Make scripts executable:

```bash
chmod +x src/record.py src/watchdog.sh
```

Add to `/etc/rc.local` (or your system’s autostart file):

```bash
nohup /path/to/py2-rtsp-recorder/src/watchdog.sh > /dev/null 2>&1 &
```

---

## Playback & Conversion

The recorded files are raw H.264 elementary streams.

### Direct Playback

- **VLC Media Player** → Opens `.h264` files directly
- **MPV**
  ```bash
  mpv recording.h264
  ```

### Convert to MP4

Since the stream is already H.264, you can wrap it into an MP4 container without quality loss (very fast on a modern PC):

```bash
ffmpeg -i input.h264 -c copy output.mp4
```

---

## Troubleshooting

**No Session ID / Auth Failed**  
Check `creds.txt`. Some cameras require specific `User-Agent` headers (adjustable in `record.py`).

**Gray artifacts at start**  
The script waits for an I-Frame (Keyframe) before writing to disk to ensure clean video files.

**Audio?**  
This version is optimized for **video only** to ensure maximum stability on weak hardware.

---

## License

MIT License — feel free to modify and use on any potato hardware you have! 🥔
