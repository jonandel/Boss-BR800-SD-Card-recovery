""" Run this Python code in VS Code studio as admin
    Specifically written for the Boss BR-800, this script will help you recover audio sessions recorded as Sketches from a potentially corrupted 
    SD card, or simply when the unit fails to save the recording due to power loss during finishing

    This script will::
    1. List physical drives to identify the SD card.
    2. Create a bit-for-bit clone of the SD card to a local image file.
    3. Scan the image for RIFF headers and carve out WAV files based on user-defined size.
"""
import os
import subprocess

def format_size(size_bytes):
    try:
        size_bytes = int(size_bytes)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0: return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
    except: return "Unknown"

def get_physical_drives():
    drives = []
    try:
        cmd = 'wmic diskdrive get Model, Name, Size /format:list'
        output = subprocess.check_output(cmd, shell=True).decode()
        blocks = output.strip().split('\r\r\n\r\r\n')
        for block in blocks:
            drive_info = {}
            for line in block.split('\r\r\n'):
                if '=' in line:
                    key, val = line.split('=', 1)
                    drive_info[key.strip()] = val.strip()
            if drive_info:
                drive_info['ReadableSize'] = format_size(drive_info.get('Size', 0))
                drives.append(drive_info)
    except Exception as e:
        print(f"Error listing drives: {e}")
    return drives

def clone_disk(drive_id, img_path):
    print(f"\n[1/2] Cloning {drive_id} to {img_path}...")
    try:
        buffer_size = 1024 * 1024
        with open(drive_id, 'rb') as src, open(img_path, 'wb') as dst:
            while True:
                chunk = src.read(buffer_size)
                if not chunk: break
                dst.write(chunk)
        return True
    except Exception as e:
        # If we have a massive file, it likely finished despite the error
        if os.path.exists(img_path) and os.path.getsize(img_path) > 1e9:
            print(f"\nNote: Cloning stopped with error ({e}), but image looks complete.")
            return True
        print(f"\nCloning failed: {e}")
        return False

def carve_audio(img_path, out_dir, hours):
    if not os.path.exists(out_dir): os.makedirs(out_dir)
    
    # 16-bit, 44.1kHz, Stereo = 176,400 bytes/sec
    carve_bytes = int(hours * 3600 * 176400)
    file_size = os.path.getsize(img_path)
    
    print(f"\n[2/2] Scanning {os.path.basename(img_path)}...")
    print(f"Carving {hours}h (~{format_size(carve_bytes)}) per header found.")

    with open(img_path, "rb") as f:
        offset = 0
        chunk_size = 10 * 1024 * 1024
        count = 0
        while offset < file_size:
            f.seek(offset)
            chunk = f.read(chunk_size + 4)
            if not chunk: break
            
            idx = 0
            while True:
                idx = chunk.find(b'RIFF', idx)
                if idx == -1 or idx > chunk_size: break
                
                # Double-check for 'WAVE' sub-header
                f.seek(offset + idx + 8)
                if f.read(4) == b'WAVE':
                    count += 1
                    print(f"Match {count} found at byte {offset + idx}")
                    f.seek(offset + idx)
                    data = f.read(carve_bytes)
                    with open(os.path.join(out_dir, f"recovery_{count}.wav"), "wb") as out:
                        out.write(data)
                idx += 1
            offset += chunk_size
    print(f"\nFinished. Extracted {count} files to {out_dir}")

if __name__ == "__main__":
    BASE = os.path.dirname(os.path.abspath(__file__))
    IMG_PATH = os.path.join(BASE, "SDCARD.bin")
    OUT_DIR = os.path.join(BASE, "recovered_audio")

    # If the image doesn't exist, we must clone
    if not os.path.exists(IMG_PATH):
        drives = get_physical_drives()
        for i, d in enumerate(drives):
            print(f"[{i}] {d['Model']} ({d['ReadableSize']})")
        
        choice = int(input("\nSelect Drive ID: "))
        hours_input = float(input("Hours to carve: "))
        
        if clone_disk(drives[choice]['Name'], IMG_PATH):
            carve_audio(IMG_PATH, OUT_DIR, hours_input)
    else:
        # If image EXISTS, just carve!
        print(f"Found existing image: {IMG_PATH}")
        hours_input = float(input("Hours to carve from existing image: "))
        carve_audio(IMG_PATH, OUT_DIR, hours_input)
