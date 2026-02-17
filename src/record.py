#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Lightweight RTSP Recorder for Python 2 / Old Hardware
Features:
- Raw H.264 extraction (no ffmpeg needed)
- Digest Authentication support
- Automatic file rotation (hourly)
- Auto-Cleanup of old recordings
- Low CPU usage (direct stream copy)
"""

import socket, hashlib, os, time, sys

# --- CONFIGURATION ---
# Load credentials from file (user\npass)
CRED_FILE = '/mnt/pools/A/A0/IP-Cam/creds.txt'
HOST = '192.168.0.225'
PORT = 554
STREAM_URI = '/stream1'
# Recording destination
DEST = '/mnt/pools/A/A0/IP-Cam/recordings'
# Segmentation and retention
SEGMENT_SECONDS = 3600  # 1 Hour
RETENTION_DAYS = 14     # Keep 14 days
# Network buffer
BUFFER_SIZE = 65536
USER_AGENT = 'curl/7.42.1'

# --- CONSTANTS ---
START_CODE = '\x00\x00\x00\x01'

def load_creds():
    try:
        with open(CRED_FILE, 'r') as f:
            user = f.readline().strip()
            pw = f.readline().strip()
        return user, pw
    except IOError:
        print "[ERROR] Could not read credentials from %s" % CRED_FILE
        sys.exit(1)

USER, PASS = load_creds()
URI = 'rtsp://%s:%d%s' % (HOST, PORT, STREAM_URI)

def cleanup_old_files():
    """Deletes files older than RETENTION_DAYS"""
    now = time.time()
    cutoff = now - (RETENTION_DAYS * 86400)
    print '[CLEANUP] Checking for old files...'
    
    count = 0
    # Clean files
    for root, dirs, files in os.walk(DEST):
        for name in files:
            if name.endswith('.h264'):
                fpath = os.path.join(root, name)
                try:
                    if os.path.getmtime(fpath) < cutoff:
                        os.remove(fpath)
                        count += 1
                except Exception, e:
                    print '[ERROR] Cleanup failed for %s: %s' % (name, e)
    
    # Clean empty directories
    for root, dirs, files in os.walk(DEST, topdown=False):
        for name in dirs:
            try:
                os.rmdir(os.path.join(root, name))
            except: pass
            
    if count > 0:
        print '[CLEANUP] Deleted %d old files.' % count

def digest_auth(method, uri, realm, nonce):
    ha1 = hashlib.md5('%s:%s:%s' % (USER, realm, PASS)).hexdigest()
    ha2 = hashlib.md5('%s:%s' % (method, uri)).hexdigest()
    response = hashlib.md5('%s:%s:%s' % (ha1, nonce, ha2)).hexdigest()
    return 'Digest username="%s", realm="%s", nonce="%s", uri="%s", response="%s"' % (USER, realm, nonce, uri, response)

def recv_exact(s, n):
    data = ''
    while len(data) < n:
        chunk = s.recv(n - len(data))
        if not chunk: raise Exception('Socket closed')
        data += chunk
    return data

def setup_rtsp(s):
    cseq = 1
    # 1. OPTIONS & DESCRIBE (Handshake)
    s.sendall('OPTIONS %s RTSP/1.0\r\nCSeq: 1\r\nUser-Agent: %s\r\n\r\n' % (URI, USER_AGENT))
    s.recv(4096)
    
    s.sendall('DESCRIBE %s RTSP/1.0\r\nCSeq: 2\r\nUser-Agent: %s\r\nAccept: application/sdp\r\n\r\n' % (URI, USER_AGENT))
    resp = s.recv(4096)
    
    nonce = realm = ''
    for line in resp.splitlines():
        if 'nonce="' in line:
            nonce = line.split('nonce="')[1].split('"')[0]
            realm = line.split('realm="')[1].split('"')[0]
            
    # 2. DESCRIBE Auth
    auth = digest_auth('DESCRIBE', URI, realm, nonce)
    s.sendall('DESCRIBE %s RTSP/1.0\r\nCSeq: 3\r\nAuthorization: %s\r\nUser-Agent: %s\r\nAccept: application/sdp\r\n\r\n' % (URI, auth, USER_AGENT))
    s.recv(8192)

    # 3. SETUP Video Only (Track 1)
    track1 = URI + '/track1'
    auth = digest_auth('SETUP', track1, realm, nonce)
    s.sendall('SETUP %s RTSP/1.0\r\nCSeq: 4\r\nAuthorization: %s\r\nUser-Agent: %s\r\nTransport: RTP/AVP/TCP;unicast;interleaved=0-1\r\n\r\n' % (track1, auth, USER_AGENT))
    resp = s.recv(4096)
    
    session = ''
    for line in resp.splitlines():
        if line.lower().startswith('session:'):
            session = line.split(':')[1].strip().split(';')[0]
            
    # 4. PLAY
    auth = digest_auth('PLAY', URI, realm, nonce)
    s.sendall('PLAY %s RTSP/1.0\r\nCSeq: 5\r\nAuthorization: %s\r\nUser-Agent: %s\r\nSession: %s\r\nRange: npt=0.000-\r\n\r\n' % (URI, auth, USER_AGENT, session))
    s.recv(4096)
    return session

class VideoWriter:
    def __init__(self):
        # Structure: DEST / YYYY-MM / DD / HH-MM.h264
        now = time.localtime()
        month_dir = os.path.join(DEST, time.strftime('%Y-%m', now))
        day_dir = os.path.join(month_dir, time.strftime('%d', now))
        if not os.path.exists(day_dir): os.makedirs(day_dir)
        fname = time.strftime('%H-%M.h264', now)
        self.fpath = os.path.join(day_dir, fname)
        print '[REC] Start File: %s' % self.fpath
        self.f = open(self.fpath, 'wb', BUFFER_SIZE)
        self.bytes_written = 0
        self.has_keyframe = False
    
    def write(self, data):
        # Strip RTP Header (12 bytes)
        if len(data) <= 12: return
        payload = data[12:]
        nal_header = ord(payload[0])
        nal_type = nal_header & 0x1F
        
        # Wait for Keyframe (SPS/PPS/IDR)
        if not self.has_keyframe:
            is_key = False
            if nal_type == 7 or nal_type == 5: is_key = True
            elif nal_type == 28 and len(payload) > 1 and (ord(payload[1]) & 0x1F) == 5: is_key = True
            if is_key: 
                print '[INFO] Keyframe detected. Recording...'
                self.has_keyframe = True
            else: return

        # H.264 Reassembly (Handle FU-A Fragmentation)
        if nal_type == 28: # FU-A
            if len(payload) < 2: return
            fu_header = ord(payload[1])
            if fu_header & 0x80: # Start bit
                reconstructed = (nal_header & 0xE0) | (fu_header & 0x1F)
                self.f.write(START_CODE + chr(reconstructed) + payload[2:])
                self.bytes_written += len(payload) + 3
            else:
                self.f.write(payload[2:])
                self.bytes_written += len(payload) - 2
        else: # Single NAL
            self.f.write(START_CODE + payload)
            self.bytes_written += len(payload) + 4

    def close(self):
        self.f.close()
        return self.bytes_written

def record():
    if not os.path.exists(DEST): os.makedirs(DEST)
    
    # Run cleanup once per session start
    try: cleanup_old_files()
    except Exception, e: print '[WARN] Cleanup Error:', e

    s = socket.socket()
    s.settimeout(30) # RTSP Keepalive timeout
    print '[CONN] Connecting to %s...' % HOST
    try:
        s.connect((HOST, PORT))
        session = setup_rtsp(s)
    except Exception, e:
        print '[ERROR] Connection/Setup failed:', e
        s.close()
        return

    writer = VideoWriter()
    start_time = time.time()
    
    try:
        while True:
            # Hourly rotation (Hardcut)
            if time.time() - start_time > SEGMENT_SECONDS and writer.has_keyframe:
                mb = writer.close() / 1048576.0
                print '[CUT] Segment finished (%.1f MB)' % mb
                
                # Check for cleanup again during rotation
                try: cleanup_old_files()
                except: pass
                
                writer = VideoWriter()
                start_time = time.time()
            
            # Read RTP Packet
            header = ''
            while len(header) < 4:
                try:
                    chunk = s.recv(4 - len(header))
                    if not chunk: raise Exception('Stream closed by remote')
                    header += chunk
                except socket.timeout:
                    # Send RTSP Keepalive
                    try: s.sendall('OPTIONS %s RTSP/1.0\r\nCSeq: 99\r\nSession: %s\r\nUser-Agent: %s\r\n\r\n' % (URI, session, USER_AGENT))
                    except: pass
                    continue
                
            if header[0] == '$':
                channel = ord(header[1])
                length = (ord(header[2]) << 8) | ord(header[3])
                data = recv_exact(s, length)
                # Channel 0 is usually Video
                if channel == 0: writer.write(data)
                    
    except Exception, e:
        print '[ERROR] Stream loop:', e
    finally:
        writer.close()
        s.close()

if __name__ == "__main__":
    while True:
        try:
            record()
        except KeyboardInterrupt:
            print "\nStopping..."
            sys.exit(0)
        except Exception, e:
            print '[RESTART] Restarting in 10s...', e
            time.sleep(10)
