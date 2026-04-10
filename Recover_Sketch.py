import os
import struct
import subprocess

def get_drive_list():
    """Identifies physical drives on Windows."""
    print("\n--- Physical Drive Map ---")
    try:
        # Requires Admin privileges
        output = subprocess.check_output('wmic diskdrive get DeviceID, Model, Size /format:list', shell=True).decode()
        print(output)
    except:
        print("Could not retrieve drive list. Run as Administrator.")

def create_disk_image(physical_drive, image_path):
    """Clones the SD card to a local file."""
    print(f"\n[1/3] Cloning {physical_drive} to {image_path}...")
    try:
        buffer_size = 1024 * 1024 # 1MB buffer
        with open(physical_drive, 'rb') as disk, open(image_path, 'wb') as image:
            while True:
                chunk = disk.read(buffer_size)
                if not chunk: break
                image.write(chunk)
        print("Cloning Complete.")
        return True
    except Exception as e:
        print(f"ERROR during cloning: {e}")
        return False

def scan_and_extract(image_path, output_dir, hours):
    """Scans for WAV headers and carves based on duration."""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Calculation: 176,400 bytes per second for 16-bit/44.1kHz Stereo
    bytes_per_second = 176400
    carve_size = int(hours * 3600 * bytes_per_second)
    
    file_size = os.path.getsize(image_path)
    print(f"\n[2/3] Scanning for WAV headers. Target carve: {hours} hours (~{carve_size/1e9:.2f} GB)")
    
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
                
                # Verify it's a WAVE file
                f.seek(abs_pos + 8)
                if f.read(4) == b'WAVE':
                    match_count += 1
                    print(f"Found WAV Header #{match_count} at byte {abs_pos}")
                    
                    # Carve the data
                    f.seek(abs_pos)
                    data = f.read(carve_size)
                    out_file = os.path.join(output_dir, f"recovered_session_{match_count}.wav")
                    with open(out_file, "wb") as out:
                        out.write(data)
                
                idx += 1
            offset += chunk_size

if __name__ == "__main__":
    print("=== BR-800 TIME-BASED RECOVERY TOOL ===")
    
    get_drive_list()
    drive_id = input("Enter Drive ID (e.g., \\\\.\\PhysicalDrive1): ").strip()
    img_name = input("Enter name for Disk Image (e.g., SD_Clone.bin): ").strip()
    out_path = input("Enter recovery folder: ").strip()
    
    # New Time Input
    try:
        rec_hours = float(input("How many hours of audio to carve per header? (e.g., 3.5): "))
    except ValueError:
        print("Invalid input. Using 4 hours as default.")
        rec_hours = 4.0

    if create_disk_image(drive_id, img_name):
        scan_and_extract(img_name, out_path, rec_hours)
        print(f"\n[3/3] Done. Check {out_path} for your files.")
