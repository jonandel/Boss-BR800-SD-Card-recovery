""" Run this Python code in VS Code studio as admin
    Specifically written for the Boss BR-800, this script will help you recover audio sessions from a potentially corrupted SD card.

    This script will::
    1. List physical drives to identify the SD card.
    2. Create a bit-for-bit clone of the SD card to a local image file.
    3. Scan the image for RIFF headers and carve out WAV files based on user-defined size.
"""
import os
import struct
import subprocess

def format_size(size_bytes):
    """Converts bytes into a human-readable format (GB, MB, KB)."""
    try:
        size_bytes = int(size_bytes)
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
    except (ValueError, TypeError):
        return "Unknown"

def get_physical_drives():
    """Parses wmic output into a selectable list with readable sizes."""
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
                # Add the human-readable size for the display
                drive_info['ReadableSize'] = format_size(drive_info.get('Size', 0))
                drives.append(drive_info)
    except Exception as e:
        print(f"Error retrieving drive list: {e}")
    return drives

def create_disk_image(physical_drive, image_path):
    """Clones the SD card to a local file."""
    print(f"\n[1/3] Cloning {physical_drive} to {image_path}...")
    try:
        buffer_size = 1024 * 1024 
        with open(physical_drive, 'rb') as disk, open(image_path, 'wb') as image:
            while True:
                chunk = disk.read(buffer_size)
                if not chunk: break
                image.write(chunk)
        print("Cloning Complete.")
        return True
    except PermissionError:
        print("\nERROR: Access Denied. Run VS Code/Terminal as Administrator.")
        return False
    except Exception as e:
        print(f"\nERROR: {e}")
        return False

def scan_and_extract(image_path, output_dir, hours):
    """Scans for WAV headers and carves (16-bit/44.1kHz Stereo)."""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 44100Hz * 2 bytes * 2 channels = 176,400 bytes/sec
    bytes_per_second = 176400
    carve_size = int(hours * 3600 * bytes_per_second)
    
    file_size = os.path.getsize(image_path)
    print(f"\n[2/3] Scanning for WAV headers. Carving {hours}h per match (~{format_size(carve_size)})")
    
    with open(image_path, "rb") as f:
        offset = 0
        chunk_size = 10 * 1024 * 1024
        match_count = 0
        
        while offset < file_size:
            f.seek(offset)
            chunk = f.read(chunk_size + 4)
            if not chunk: break
            
            idx = 0
            while True:
                idx = chunk.find(b'RIFF', idx)
                if idx == -1 or idx > chunk_size: break
                
                abs_pos = offset + idx
                f.seek(abs_pos + 8)
                if f.read(4) == b'WAVE':
                    match_count += 1
                    print(f"Found WAV Header #{match_count} at byte {abs_pos}")
                    
                    f.seek(abs_pos)
                    data = f.read(carve_size)
                    out_file = os.path.join(output_dir, f"recovered_session_{match_count}.wav")
                    with open(out_file, "wb") as out:
                        out.write(data)
                idx += 1
            offset += chunk_size

if __name__ == "__main__":
    print("=== BR-800 AUTOMATED FORENSIC TOOL ===\n")
    
    drive_list = get_physical_drives()
    if not drive_list:
        print("No physical drives found. Try running as Admin.")
        exit()

    print(f"{'ID':<4} | {'Model':<30} | {'Size':<10}")
    print("-" * 50)
    for i, d in enumerate(drive_list):
        print(f"[{i}]  | {d.get('Model', 'Unknown'):<30} | {d.get('ReadableSize', 'Unknown')}")
    
    try:
        choice = int(input("\nSelect the ID of your SD Card: "))
        selected_drive = drive_list[choice]['Name']
    except (ValueError, IndexError):
        print("Invalid selection. Exiting.")
        exit()

    img_name = input("Enter name for Disk Image (e.g., rehearsal_dump.bin): ").strip()
    out_path = input("Enter recovery folder name: ").strip()
    try:
        rec_hours = float(input("How many hours of audio to carve? (e.g., 3.5): "))
    except ValueError:
        rec_hours = 4.0

    if create_disk_image(selected_drive, img_name):
        scan_and_extract(img_name, out_path, rec_hours)
        print(f"\n[3/3] Recovery Complete. Files are in: {out_path}")
