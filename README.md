# Py2-RTSP-Recorder 📹

A lightweight, robust RTSP video recorder designed for **legacy hardware** (NAS, Embedded Systems) running **Python 2.5**. 

It connects to an IP Camera via RTSP, authenticates (Digest/Basic), extracts the raw H.264 stream, and saves it to disk with zero transcoding.

## Features

- 🐍 **Pure Python 2**: No external libraries (like ffmpeg/opencv) required. Standard library only.
- 🚀 **Zero-Copy Performance**: Writes raw H.264 NAL units directly to disk. Minimal CPU usage (<5% on 400MHz ARM).
- 🔄 **Auto-Rotation**: Creates hourly segments organized by `YYYY-MM/DD/HH-MM.h264`.
- 🧹 **Auto-Cleanup**: Automatically deletes recordings older than X days.
- 🛡️ **Robustness**: Handles network drops, camera reboots, and stream fragmentation (FU-A).

## Setup

1. **Clone the repo** to your NAS/Device:
   ```bash
   git clone https://github.com/itsXactlY/py2-rtsp-recorder.git
   cd py2-rtsp-recorder
