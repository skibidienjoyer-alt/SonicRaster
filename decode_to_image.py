import wave
import struct
import os
import glob
import zlib
from PIL import Image

# ---------- CONFIG ----------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WAV_FOLDER = os.path.join(SCRIPT_DIR, "wav_output")
OUT_FOLDER = os.path.join(SCRIPT_DIR, "decoded_images")

os.makedirs(OUT_FOLDER, exist_ok=True)

# ---------- DECODING ----------
def decode_header(data):
    """
    Decode header from first 13 bytes
    Returns: (width, height, original_width, original_height, is_compressed, uncompressed_size)
    """
    width, height, original_w, original_h = struct.unpack('<HHHH', data[:8])
    is_compressed = struct.unpack('B', data[8:9])[0] == 1
    uncompressed_size = struct.unpack('<I', data[9:13])[0]
    
    return width, height, original_w, original_h, is_compressed, uncompressed_size

# ---------- FIND WAV FILES ----------
wav_pattern = os.path.join(WAV_FOLDER, "*_encoded.wav")
wav_files = glob.glob(wav_pattern)

if not wav_files:
    print(f"No encoded WAV files found in: {WAV_FOLDER}")
    print(f"Please run the encoder script first!")
    exit()

print(f"Found {len(wav_files)} WAV file(s)")
print("-" * 50)

# ---------- DECODE EACH WAV ----------
successful = 0
failed = 0

for wav_file in wav_files:
    print(f"\nDecoding: {os.path.basename(wav_file)}")
    
    try:
        # Open WAV file
        with wave.open(wav_file, 'rb') as wav:
            audio_data = wav.readframes(wav.getnframes())
        
        # Decode header (first 13 bytes)
        w, h, original_w, original_h, is_compressed, uncompressed_size = decode_header(audio_data)
        
        print(f"  Encoded size: {w}x{h} pixels")
        print(f"  Original size: {original_w}x{original_h} pixels")
        print(f"  Compression: {'YES' if is_compressed else 'NO'}")
        
        # Extract pixel data (after 13-byte header)
        pixel_data_raw = audio_data[13:]
        
        # Decompress if needed
        if is_compressed:
            print(f"  Decompressing {len(pixel_data_raw):,} bytes...")
            pixel_data = zlib.decompress(pixel_data_raw)
            print(f"  ✓ Decompressed to {len(pixel_data):,} bytes")
        else:
            pixel_data = pixel_data_raw
        
        # Create image
        img = Image.new('RGB', (w, h), color=(0, 0, 0))
        pixels = img.load()
        
        # Decode pixels
        offset = 0
        pixel_count = 0
        
        for y in range(h):
            for x in range(w):
                if offset + 2 < len(pixel_data):
                    r = pixel_data[offset]
                    g = pixel_data[offset + 1]
                    b = pixel_data[offset + 2]
                    
                    pixels[x, y] = (r, g, b)
                    pixel_count += 1
                    
                    offset += 3
        
        # Resize to original dimensions
        img_final = img.resize((original_w, original_h), Image.Resampling.LANCZOS)
        
        # Save
        base_name = os.path.splitext(os.path.basename(wav_file))[0].replace("_encoded", "")
        out_file = os.path.join(OUT_FOLDER, f"{base_name}_decoded.png")
        img_final.save(out_file)
        
        print(f"  ✓ Decoded {pixel_count:,} pixels")
        print(f"  ✓ Resized to original dimensions")
        print(f"  ✓ Saved: {out_file}")
        
        successful += 1
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        failed += 1

print("\n" + "=" * 50)
print(f"Decoding complete! Success: {successful} | Failed: {failed}")