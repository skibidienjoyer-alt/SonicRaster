import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import wave
import struct
import os
import zlib
from PIL import Image
import threading

class ImageWAVConverter:
    def __init__(self, root):
        self.root = root
        self.root.title("Image to WAV Converter")
        self.root.geometry("700x500")
        self.root.configure(bg='#C0C0C0')
        
        # Configuration
        self.sample_rate = 44100
        self.channels = 1
        self.sample_width = 2
        self.compression_enabled = tk.BooleanVar(value=True)
        self.compression_level = tk.IntVar(value=9)
        self.quality_mode = tk.StringVar(value="HIGH")
        
        self.quality_settings = {
            "LOW": 256,
            "MEDIUM": 512,
            "HIGH": 1024,
            "MAX": 2048,
            "ORIGINAL": None
        }
        
        # Create menu bar
        menubar = tk.Menu(root)
        root.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Exit", command=root.quit)
        
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)
        
        # Create main container with border
        main_frame = tk.Frame(root, bg='#C0C0C0', relief=tk.SUNKEN, bd=2)
        main_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Toolbar
        toolbar = tk.Frame(main_frame, bg='#C0C0C0', relief=tk.RAISED, bd=2)
        toolbar.pack(side='top', fill='x', padx=2, pady=2)
        
        tk.Button(toolbar, text="Encode Images", width=15, height=2, 
                 relief=tk.RAISED, bd=2, command=self.encode_images).pack(side='left', padx=2, pady=2)
        
        tk.Button(toolbar, text="Decode WAV", width=15, height=2,
                 relief=tk.RAISED, bd=2, command=self.decode_wav).pack(side='left', padx=2, pady=2)
        
        tk.Frame(toolbar, width=2, bg='#808080', relief=tk.SUNKEN, bd=1).pack(side='left', fill='y', padx=5)
        
        tk.Button(toolbar, text="Clear Log", width=12, height=2,
                 relief=tk.RAISED, bd=2, command=self.clear_log).pack(side='left', padx=2, pady=2)
        
        # Settings panel
        settings_frame = tk.LabelFrame(main_frame, text="Settings", bg='#C0C0C0', 
                                      relief=tk.GROOVE, bd=2, padx=10, pady=10)
        settings_frame.pack(side='top', fill='x', padx=5, pady=5)
        
        # Quality settings
        quality_frame = tk.Frame(settings_frame, bg='#C0C0C0')
        quality_frame.pack(side='left', padx=10)
        
        tk.Label(quality_frame, text="Quality Mode:", bg='#C0C0C0').pack(anchor='w')
        quality_combo = ttk.Combobox(quality_frame, textvariable=self.quality_mode, 
                                    state='readonly', width=12)
        quality_combo['values'] = ('LOW', 'MEDIUM', 'HIGH', 'MAX', 'ORIGINAL')
        quality_combo.pack()
        
        # Compression settings
        compression_frame = tk.Frame(settings_frame, bg='#C0C0C0')
        compression_frame.pack(side='left', padx=10)
        
        tk.Checkbutton(compression_frame, text="Enable Compression", 
                      variable=self.compression_enabled, bg='#C0C0C0').pack(anchor='w')
        
        level_frame = tk.Frame(compression_frame, bg='#C0C0C0')
        level_frame.pack(fill='x')
        tk.Label(level_frame, text="Level (0-9):", bg='#C0C0C0').pack(side='left')
        tk.Spinbox(level_frame, from_=0, to=9, textvariable=self.compression_level, 
                  width=5, relief=tk.SUNKEN, bd=1).pack(side='left', padx=5)
        
        # Separator
        separator = tk.Frame(main_frame, height=2, bg='#808080', relief=tk.SUNKEN, bd=1)
        separator.pack(fill='x', padx=5, pady=5)
        
        # Log panel
        log_frame = tk.LabelFrame(main_frame, text="Log", bg='#C0C0C0', 
                                 relief=tk.GROOVE, bd=2)
        log_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, 
                                                  bg='white', fg='black',
                                                  relief=tk.SUNKEN, bd=2,
                                                  font=('Courier', 9))
        self.log_text.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Status bar
        self.status_bar = tk.Label(root, text="Ready", bd=1, relief=tk.SUNKEN, 
                                  anchor='w', bg='#C0C0C0')
        self.status_bar.pack(side='bottom', fill='x')
        
        self.log("Application started")
    
    def log(self, message):
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def clear_log(self):
        self.log_text.delete(1.0, tk.END)
    
    def update_status(self, message):
        self.status_bar.config(text=message)
        self.root.update_idletasks()
    
    def show_about(self):
        messagebox.showinfo("About", 
                           "Image to WAV Converter\n\n" +
                           "Encodes images into WAV audio files\n" +
                           "and decodes them back to images.\n\n" +
                           "Version 1.0")
    
    def encode_header(self, width, height, original_width, original_height, is_compressed, uncompressed_size):
        header = struct.pack('<HHHH', width, height, original_width, original_height)
        header += struct.pack('B', 1 if is_compressed else 0)
        header += struct.pack('<I', uncompressed_size)
        return header
    
    def decode_header(self, data):
        width, height, original_w, original_h = struct.unpack('<HHHH', data[:8])
        is_compressed = struct.unpack('B', data[8:9])[0] == 1
        uncompressed_size = struct.unpack('<I', data[9:13])[0]
        return width, height, original_w, original_h, is_compressed, uncompressed_size
    
    def encode_images(self):
        files = filedialog.askopenfilenames(
            title="Select Images to Encode",
            filetypes=[
                ("All Images", "*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.tif *.webp"),
                ("PNG files", "*.png"),
                ("JPEG files", "*.jpg *.jpeg"),
                ("All files", "*.*")
            ]
        )
        
        if not files:
            return
        
        output_dir = filedialog.askdirectory(title="Select Output Directory")
        if not output_dir:
            return
        
        def encode_thread():
            self.update_status("Encoding...")
            successful = 0
            failed = 0
            
            max_size = self.quality_settings[self.quality_mode.get()]
            enable_compression = self.compression_enabled.get()
            compression_level = self.compression_level.get()
            
            self.log(f"--- Encoding {len(files)} file(s) ---")
            self.log(f"Quality: {self.quality_mode.get()}")
            self.log(f"Compression: {'ON (level ' + str(compression_level) + ')' if enable_compression else 'OFF'}")
            self.log("-" * 50)
            
            for image_file in files:
                try:
                    self.log(f"\nProcessing: {os.path.basename(image_file)}")
                    
                    img = Image.open(image_file)
                    
                    if img.mode in ('RGBA', 'LA', 'P'):
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        if img.mode == 'P':
                            img = img.convert('RGBA')
                        background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                        img = background
                    else:
                        img = img.convert("RGB")
                    
                    original_w, original_h = img.size
                    self.log(f"  Original: {original_w}x{original_h}")
                    
                    if max_size is not None:
                        img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                        w, h = img.size
                        self.log(f"  Encoded: {w}x{h}")
                    else:
                        w, h = original_w, original_h
                    
                    pixel_data = bytearray()
                    for y in range(h):
                        for x in range(w):
                            r, g, b = img.getpixel((x, y))
                            pixel_data.extend(struct.pack('BBB', r, g, b))
                    
                    uncompressed_size = len(pixel_data)
                    
                    if enable_compression:
                        compressed_data = zlib.compress(bytes(pixel_data), level=compression_level)
                        ratio = (len(compressed_data) / uncompressed_size) * 100
                        self.log(f"  Compressed: {uncompressed_size:,} -> {len(compressed_data):,} bytes ({ratio:.1f}%)")
                        final_data = compressed_data
                    else:
                        final_data = pixel_data
                    
                    base_name = os.path.splitext(os.path.basename(image_file))[0]
                    out_file = os.path.join(output_dir, f"{base_name}_encoded.wav")
                    
                    with wave.open(out_file, 'wb') as wav:
                        wav.setnchannels(self.channels)
                        wav.setsampwidth(self.sample_width)
                        wav.setframerate(self.sample_rate)
                        
                        audio_data = bytearray()
                        audio_data.extend(self.encode_header(w, h, original_w, original_h, 
                                                            enable_compression, uncompressed_size))
                        audio_data.extend(final_data)
                        
                        if len(audio_data) % 2 != 0:
                            audio_data.append(0)
                        
                        wav.writeframes(bytes(audio_data))
                    
                    file_size = os.path.getsize(out_file)
                    self.log(f"  Saved: {os.path.basename(out_file)} ({file_size/1024:.1f} KB)")
                    successful += 1
                    
                except Exception as e:
                    self.log(f"  ERROR: {str(e)}")
                    failed += 1
            
            self.log("\n" + "=" * 50)
            self.log(f"Complete! Success: {successful} | Failed: {failed}")
            self.update_status("Ready")
            messagebox.showinfo("Encoding Complete", 
                              f"Encoded {successful} file(s)\nFailed: {failed}")
        
        threading.Thread(target=encode_thread, daemon=True).start()
    
    def decode_wav(self):
        files = filedialog.askopenfilenames(
            title="Select WAV Files to Decode",
            filetypes=[
                ("WAV files", "*.wav"),
                ("All files", "*.*")
            ]
        )
        
        if not files:
            return
        
        output_dir = filedialog.askdirectory(title="Select Output Directory")
        if not output_dir:
            return
        
        def decode_thread():
            self.update_status("Decoding...")
            successful = 0
            failed = 0
            
            self.log(f"\n--- Decoding {len(files)} file(s) ---")
            self.log("-" * 50)
            
            for wav_file in files:
                try:
                    self.log(f"\nProcessing: {os.path.basename(wav_file)}")
                    
                    with wave.open(wav_file, 'rb') as wav:
                        audio_data = wav.readframes(wav.getnframes())
                    
                    w, h, original_w, original_h, is_compressed, uncompressed_size = self.decode_header(audio_data)
                    
                    self.log(f"  Encoded: {w}x{h}")
                    self.log(f"  Original: {original_w}x{original_h}")
                    self.log(f"  Compression: {'YES' if is_compressed else 'NO'}")
                    
                    pixel_data_raw = audio_data[13:]
                    
                    if is_compressed:
                        pixel_data = zlib.decompress(pixel_data_raw)
                        self.log(f"  Decompressed: {len(pixel_data):,} bytes")
                    else:
                        pixel_data = pixel_data_raw
                    
                    img = Image.new('RGB', (w, h), color=(0, 0, 0))
                    pixels = img.load()
                    
                    offset = 0
                    for y in range(h):
                        for x in range(w):
                            if offset + 2 < len(pixel_data):
                                r = pixel_data[offset]
                                g = pixel_data[offset + 1]
                                b = pixel_data[offset + 2]
                                pixels[x, y] = (r, g, b)
                                offset += 3
                    
                    img_final = img.resize((original_w, original_h), Image.Resampling.LANCZOS)
                    
                    base_name = os.path.splitext(os.path.basename(wav_file))[0].replace("_encoded", "")
                    out_file = os.path.join(output_dir, f"{base_name}_decoded.png")
                    img_final.save(out_file)
                    
                    self.log(f"  Saved: {os.path.basename(out_file)}")
                    successful += 1
                    
                except Exception as e:
                    self.log(f"  ERROR: {str(e)}")
                    failed += 1
            
            self.log("\n" + "=" * 50)
            self.log(f"Complete! Success: {successful} | Failed: {failed}")
            self.update_status("Ready")
            messagebox.showinfo("Decoding Complete", 
                              f"Decoded {successful} file(s)\nFailed: {failed}")
        
        threading.Thread(target=decode_thread, daemon=True).start()

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageWAVConverter(root)
    root.mainloop()