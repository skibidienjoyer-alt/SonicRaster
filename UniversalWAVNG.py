import wave
import struct
import os
import glob
import zlib
from PIL import Image

# ---------- CONFIG ----------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_FOLDER = os.path.join(SCRIPT_DIR, "wav_output")

# QUALITY SETTINGS - Choose one:
QUALITY_MODE = "HIGH"  # Options: "LOW" (256), "MEDIUM" (512), "HIGH" (1024), "MAX" (2048), "ORIGINAL" (no resize)

QUALITY_SETTINGS = {
    "LOW": 256,
    "MEDIUM": 512,
    "HIGH": 1024,
    "MAX": 2048,
    "ORIGINAL": None  # No resizing
}

MAX_SIZE = QUALITY_SETTINGS[QUALITY_MODE]

# COMPRESSION SETTINGS
ENABLE_COMPRESSION = True  # Set to False to disable compression
COMPRESSION_LEVEL = 9  # 0-9, where 9 is maximum compression (slower but smallest)

SAMPLE_RATE = 44100
CHANNELS = 1
SAMPLE_WIDTH = 2

# Supported image extensions (PIL can open these)
SUPPORTED_EXTENSIONS = [
    '*.png', '*.jpg', '*.jpeg', '*.bmp', '*.gif', 
    '*.tiff', '*.tif', '*.webp', '*.ico', '*.ppm',
    '*.pgm', '*.pbm', '*.pnm', '*.dib', '*.eps',
    '*.im', '*.msp', '*.pcx', '*.sgi', '*.tga',
    '*.xbm'
]

os.makedirs(OUT_FOLDER, exist_ok=True)

# ---------- ENCODING ----------
def encode_header(width, height, original_width, original_height, is_compressed, uncompressed_size):
    """
    Encode header with metadata
    Format: 4 uint16 (dimensions) + 1 byte (compression flag) + 1 uint32 (uncompressed size) = 13 bytes
    """
    header = struct.pack('<HHHH', width, height, original_width, original_height)
    header += struct.pack('B', 1 if is_compressed else 0)
    header += struct.pack('<I', uncompressed_size)
    return header

# ---------- FIND IMAGE FILES ----------
image_files = []
for ext in SUPPORTED_EXTENSIONS:
    pattern = os.path.join(SCRIPT_DIR, ext)
    image_files.extend(glob.glob(pattern))
    # Also check uppercase extensions
    pattern_upper = os.path.join(SCRIPT_DIR, ext.upper())
    image_files.extend(glob.glob(pattern_upper))

# Remove duplicates
image_files = list(set(image_files))

if not image_files:
    print(f"No supported image files found in: {SCRIPT_DIR}")
    print(f"Supported formats: {', '.join([ext.replace('*.', '').upper() for ext in SUPPORTED_EXTENSIONS[:10]])}...")
    exit()

print(f"Found {len(image_files)} image file(s)")
print(f"Quality Mode: {QUALITY_MODE}")
print(f"Compression: {'ENABLED (level ' + str(COMPRESSION_LEVEL) + ')' if ENABLE_COMPRESSION else 'DISABLED'}")
print("-" * 50)

# ---------- ENCODE EACH IMAGE ----------
successful = 0
failed = 0

for image_file in image_files:
    print(f"\nEncoding: {os.path.basename(image_file)}")
    
    try:
        # Load image and convert to RGB (handles all formats including RGBA, grayscale, etc.)
        img = Image.open(image_file)
        
        # Handle transparency/alpha channels
        if img.mode in ('RGBA', 'LA', 'P'):
            # Create white background
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
            img = background
        else:
            img = img.convert("RGB")
        
        original_w, original_h = img.size
        
        print(f"  Original size: {original_w}x{original_h} pixels")
        
        # Resize if needed
        if MAX_SIZE is not None:
            img.thumbnail((MAX_SIZE, MAX_SIZE), Image.Resampling.LANCZOS)
            w, h = img.size
            print(f"  Encoded size: {w}x{h} pixels")
        else:
            w, h = original_w, original_h
            print(f"  Encoded size: ORIGINAL (no resize)")
        
        # Build pixel data
        pixel_data = bytearray()
        pixel_count = 0
        
        for y in range(h):
            for x in range(w):
                r, g, b = img.getpixel((x, y))
                pixel_data.extend(struct.pack('BBB', r, g, b))
                pixel_count += 1
        
        uncompressed_size = len(pixel_data)
        
        # Compress pixel data if enabled
        if ENABLE_COMPRESSION:
            compressed_data = zlib.compress(bytes(pixel_data), level=COMPRESSION_LEVEL)
            compression_ratio = (len(compressed_data) / uncompressed_size) * 100
            print(f"  ✓ Compressed: {uncompressed_size:,} → {len(compressed_data):,} bytes ({compression_ratio:.1f}%)")
            final_data = compressed_data
        else:
            final_data = pixel_data
        
        # Create WAV file
        base_name = os.path.splitext(os.path.basename(image_file))[0]
        out_file = os.path.join(OUT_FOLDER, f"{base_name}_encoded.wav")
        
        with wave.open(out_file, 'wb') as wav:
            wav.setnchannels(CHANNELS)
            wav.setsampwidth(SAMPLE_WIDTH)
            wav.setframerate(SAMPLE_RATE)
            
            # Build audio data: header + compressed/uncompressed pixel data
            audio_data = bytearray()
            audio_data.extend(encode_header(w, h, original_w, original_h, ENABLE_COMPRESSION, uncompressed_size))
            audio_data.extend(final_data)
            
            # Pad to even length if needed
            if len(audio_data) % 2 != 0:
                audio_data.append(0)
            
            # Write to WAV
            wav.writeframes(bytes(audio_data))
        
        # Stats
        file_size = os.path.getsize(out_file)
        original_size = original_w * original_h * 3
        
        print(f"  ✓ Encoded {pixel_count:,} pixels")
        print(f"  ✓ File size: {file_size:,} bytes ({file_size/1024:.1f} KB)")
        if ENABLE_COMPRESSION:
            savings = ((original_size - file_size) / original_size) * 100
            print(f"  ✓ Space saved vs uncompressed: {savings:.1f}%")
        print(f"  ✓ Saved: {out_file}")
        
        successful += 1
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        failed += 1

print("\n" + "=" * 50)
print(f"Encoding complete! Success: {successful} | Failed: {failed}")