""" Run this Python code in VS Code studio as admin
    Specifically written for the Boss BR-800, this script will help you recover audio sessions from a potentially corrupted SD card.

    This script will::
    1. List physical drives to identify the SD card.
    2. Create a bit-for-bit clone of the SD card to a local image file.
    3. Scan the image for RIFF headers and carve out WAV files based on user-defined size.
"""
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
    try:
        size_bytes = int(size_bytes)
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
    except:
        return "Unknown"

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
        print(f"Error retrieving drive list: {e}")
    return drives

def create_disk_image(physical_drive, image_path):
    # Ensure directory exists (though with relative paths it should)
    os.makedirs(os.path.dirname(os.path.abspath(image_path)), exist_ok=True)

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
        print("\nERROR: Access Denied. Run as Administrator!")
        return False
    except Exception as e:
        print(f"\nERROR: {e}")
        return False

def scan_and_extract(image_path, output_dir, hours):
    os.makedirs(output_dir, exist_ok=True)

    # BR-800 Standard: 16-bit, 44.1kHz, Stereo
    bytes_per_second = 176400
    carve_size = int(hours * 3600 * bytes_per_second)
    
    file_size = os.path.getsize(image_path)
    print(f"\n[2/3] Scanning for headers. Carving {hours}h per match (~{format_size(carve_size)})")
    
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
    # Anchor paths to the script's current location
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    
    print("=== BR-800 AUTOMATED FORENSIC TOOL ===")
    print(f"Working Directory: {BASE_DIR}\n")
    
    drive_list = get_physical_drives()
    if not drive_list:
        print("No drives found. Run as Admin.")
        exit()

    print(f"{'ID':<4} | {'Model':<30} | {'Size':<10}")
    print("-" * 50)
    for i, d in enumerate(drive_list):
        print(f"[{i}]  | {d.get('Model', 'Unknown'):<30} | {d.get('ReadableSize', 'Unknown')}")
    
    try:
        choice = int(input("\nSelect the ID of your SD Card: "))
        selected_drive = drive_list[choice]['Name']
    except:
        print("Invalid selection."); exit()

    # Automatic pathing
    default_img = os.path.join(BASE_DIR, "sd_clone.bin")
    default_out = os.path.join(BASE_DIR, "recovered_audio")

    img_name = input(f"Image Path [default: {default_img}]: ").strip() or default_img
    out_path = input(f"Recovery Folder [default: {default_out}]: ").strip() or default_out
    
    try:
        input_hours = input("How many hours of audio to carve? [default: 2]: ").strip()
        rec_hours = float(input_hours) if input_hours else 2.0
    except:
        rec_hours = 2.0

    if create_disk_image(selected_drive, img_name):
        scan_and_extract(img_name, out_path, rec_hours)
        print(f"\n[3/3] Success! Data saved in subdirectory.")
        print(f"Image: {img_name}")
        print(f"Audio: {out_path}")
