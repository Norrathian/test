import os
import math
import tkinter as tk
from tkinter import filedialog, ttk, scrolledtext, messagebox
from pydub import AudioSegment
import time
import requests
import re
from tkinter import simpledialog
import threading
import subprocess
import platform
import tempfile
import numpy as np

# Try to configure ImageMagick for MoviePy
def setup_moviepy():
    """Configure MoviePy with ImageMagick"""
    try:
        from moviepy.config import change_settings
        
        # Common ImageMagick installation paths for Windows
        possible_paths = [
            r"C:\Program Files\ImageMagick-7.1.1-Q16-HDRI\magick.exe",
            r"C:\Program Files\ImageMagick-7.1.0-Q16-HDRI\magick.exe",
            r"C:\Program Files\ImageMagick-7.0.11-Q16-HDRI\magick.exe",
            r"C:\Program Files\ImageMagick-7.0.10-Q16-HDRI\magick.exe",
            r"C:\Program Files\ImageMagick-7.0.9-Q16-HDRI\magick.exe",
            r"C:\Program Files\ImageMagick-7.0.8-Q16-HDRI\magick.exe",
            r"C:\Program Files\ImageMagick-7.0.7-Q16-HDRI\magick.exe",
            r"C:\Program Files\ImageMagick-7.0.6-Q16-HDRI\magick.exe",
            r"C:\Program Files\ImageMagick-7.0.5-Q16-HDRI\magick.exe",
            r"C:\Program Files\ImageMagick-7.0.4-Q16-HDRI\magick.exe",
            r"C:\Program Files\ImageMagick-7.0.3-Q16-HDRI\magick.exe",
            r"C:\Program Files\ImageMagick-7.0.2-Q16-HDRI\magick.exe",
            r"C:\Program Files\ImageMagick-7.0.1-Q16-HDRI\magick.exe",
            r"C:\Program Files\ImageMagick-7.0.0-Q16-HDRI\magick.exe",
            r"C:\Program Files\ImageMagick-6.9.12-Q16-HDRI\magick.exe",
            r"C:\Program Files\ImageMagick-6.9.11-Q16-HDRI\magick.exe",
            r"C:\Program Files\ImageMagick-6.9.10-Q16-HDRI\magick.exe",
            r"C:\Program Files\ImageMagick-6.9.9-Q16-HDRI\magick.exe",
            r"C:\Program Files\ImageMagick-6.9.8-Q16-HDRI\magick.exe",
            r"C:\Program Files\ImageMagick-6.9.7-Q16-HDRI\magick.exe",
            r"C:\Program Files\ImageMagick-6.9.6-Q16-HDRI\magick.exe",
            r"C:\Program Files\ImageMagick-6.9.5-Q16-HDRI\magick.exe",
            r"C:\Program Files\ImageMagick-6.9.4-Q16-HDRI\magick.exe",
            r"C:\Program Files\ImageMagick-6.9.3-Q16-HDRI\magick.exe",
            r"C:\Program Files\ImageMagick-6.9.2-Q16-HDRI\magick.exe",
            r"C:\Program Files\ImageMagick-6.9.1-Q16-HDRI\magick.exe",
            r"C:\Program Files\ImageMagick-6.9.0-Q16-HDRI\magick.exe"
        ]
        
        # First try to find ImageMagick in PATH
        try:
            subprocess.check_output(["magick", "-version"], stderr=subprocess.STDOUT)
            return True
        except:
            pass
            
        # Try to find ImageMagick in common installation paths
        for path in possible_paths:
            if os.path.exists(path):
                try:
                    # Test if the ImageMagick installation is working
                    subprocess.check_output([path, "-version"], stderr=subprocess.STDOUT)
                    change_settings({"IMAGEMAGICK_BINARY": path})
                    return True
                except:
                    continue
        
        # Try to find ImageMagick using registry
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\ImageMagick\Current")
            binpath = winreg.QueryValueEx(key, "BinPath")[0]
            magick_path = os.path.join(binpath, "magick.exe")
            if os.path.exists(magick_path):
                subprocess.check_output([magick_path, "-version"], stderr=subprocess.STDOUT)
                change_settings({"IMAGEMAGICK_BINARY": magick_path})
                return True
        except:
            pass
            
        return False
        
    except Exception as e:
        print(f"Error configuring ImageMagick: {e}")
        return False

# Try to set up ImageMagick for MoviePy
moviepy_configured = setup_moviepy()

def format_timestamp(seconds):
    """Convert seconds to LRC timestamp format [mm:ss.xx]"""
    minutes = math.floor(seconds / 60)
    secs = seconds % 60
    return f"[{minutes:02d}:{secs:05.2f}]"

def fetch_lyrics(artist, title):
    """Try to fetch lyrics from online API"""
    try:
        update_status(f"Searching for lyrics: {artist} - {title}...")
        
        # Clean the search terms
        artist = re.sub(r'[^\w\s]', '', artist).strip()
        title = re.sub(r'[^\w\s]', '', title).strip()
        
        # Try to fetch from API.lyrics.ovh
        url = f"https://api.lyrics.ovh/v1/{artist}/{title}"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200 and 'lyrics' in response.json():
            lyrics = response.json()['lyrics']
            # Split into lines and remove empty lines
            lines = [line.strip() for line in lyrics.split('\n') if line.strip()]
            return lines
            
        # Try alternative API or method if the first one fails
        # (Simplified for demo purposes)
        
        return None
    except Exception as e:
        print(f"Error fetching lyrics: {e}")
        return None

def align_lyrics_with_audio(lyrics, duration):
    """Align lyrics with audio duration"""
    if not lyrics:
        return []
        
    lrc_lines = []
    # Calculate time per line (distribute evenly)
    time_per_line = duration / len(lyrics)
    
    for i, line in enumerate(lyrics):
        # Calculate timestamp for this line
        time_point = i * time_per_line
        timestamp = format_timestamp(time_point)
        lrc_lines.append(f"{timestamp}{line}")
        
    return lrc_lines

def get_metadata_from_filename(filename):
    """Try to extract artist and title from filename"""
    # Common patterns: "Artist - Title" or "Title"
    parts = os.path.splitext(os.path.basename(filename))[0].split(' - ', 1)
    if len(parts) == 2:
        return parts[0], parts[1]
    else:
        return None, parts[0]

def fetch_from_lrclib(artist, title):
    """Try to fetch synchronized lyrics from LRCLib.com"""
    try:
        update_status(f"Searching LRCLib for: {artist} - {title}...")
        
        # Clean the search terms
        artist = re.sub(r'[^\w\s]', '', artist).strip()
        title = re.sub(r'[^\w\s]', '', title).strip()
        
        # First, search for the song
        search_url = "http://lrclib.net/api/search"
        params = {
            "track_name": title,
            "artist_name": artist
        }
        
        response = requests.get(search_url, params=params, timeout=10)
        
        if response.status_code == 200:
            results = response.json()
            
            if results:  # If we found any matches
                # Get the first result's ID
                track_id = results[0]["id"]
                
                # Fetch the LRC for this track
                lrc_url = f"http://lrclib.net/api/get/{track_id}"
                lrc_response = requests.get(lrc_url, timeout=10)
                
                if lrc_response.status_code == 200:
                    lrc_data = lrc_response.json()
                    if lrc_data and "syncedLyrics" in lrc_data:
                        return lrc_data["syncedLyrics"]
        
        return None
    except Exception as e:
        print(f"Error fetching from LRCLib: {e}")
        return None

def process_with_online_lyrics(mp3_path, output_path):
    """Process MP3 using online lyrics database"""
    try:
        # Get song duration
        audio = AudioSegment.from_mp3(mp3_path)
        duration = audio.duration_seconds
        
        # Try to get artist and title from filename
        artist, title = get_metadata_from_filename(mp3_path)
        
        # Ask user to confirm or provide artist and title
        if not artist:
            artist = simpledialog.askstring("Artist", "Enter artist name:", parent=root)
        else:
            artist = simpledialog.askstring("Artist", "Enter artist name:", initialvalue=artist, parent=root)
            
        title = simpledialog.askstring("Title", "Enter song title:", initialvalue=title, parent=root)
        
        if not artist or not title:
            return "Cancelled", []
        
        # First try LRCLib for synchronized lyrics
        lrc_content = fetch_from_lrclib(artist, title)
        if lrc_content:
            # Write the LRC content directly to file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(f"[ti:{title}]\n")
                f.write(f"[ar:{artist}]\n")
                f.write(f"[length:{format_timestamp(duration)[1:-1]}]\n\n")
                f.write(lrc_content)
            
            # Parse the content for display
            lines = [line for line in lrc_content.split('\n') if line.strip()]
            update_status("Successfully fetched synchronized lyrics from LRCLib")
            return "Success", lines
            
        # If LRCLib fails, try lyrics.ovh for plain lyrics
        update_status("LRCLib sync not found, trying lyrics.ovh...")
        lyrics = fetch_lyrics(artist, title)
        
        if not lyrics:
            messagebox.showinfo("Lyrics Not Found", 
                "Could not find lyrics online. Creating timestamp template instead.")
            return create_timestamp_template(mp3_path, output_path)
            
        # Align lyrics with audio
        lrc_lines = align_lyrics_with_audio(lyrics, duration)
        
        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"[ti:{title}]\n")
            f.write(f"[ar:{artist}]\n")
            f.write(f"[length:{format_timestamp(duration)[1:-1]}]\n\n")
            for line in lrc_lines:
                f.write(f"{line}\n")
                
        return "Success", lrc_lines
    except Exception as e:
        return f"Error: {e}", []

def create_timestamp_template(mp3_path, output_path, interval=2):
    """Create an LRC file with just timestamps at regular intervals"""
    try:
        # Get audio duration
        audio = AudioSegment.from_mp3(mp3_path)
        duration = audio.duration_seconds
        
        # Get filename for title
        title = os.path.splitext(os.path.basename(mp3_path))[0]
        
        # Create timestamp lines
        current_time = 0
        lines = []
        
        # Add metadata
        lines.append(f"[ti:{title}]")
        lines.append(f"[length:{format_timestamp(duration)[1:-1]}]")
        lines.append("")
        
        # Add timestamp lines
        while current_time < duration:
            timestamp = format_timestamp(current_time)
            lines.append(f"{timestamp}[Enter lyrics here]")
            current_time += interval
            
        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            for line in lines:
                f.write(f"{line}\n")
                
        return "Success", lines
    except Exception as e:
        return f"Error: {e}", []

def enter_sync_mode():
    """Enter synchronization mode for manual timestamping"""
    lyrics = []
    
    # Check if we have lyrics from file or paste area
    if sync_lyrics_file.get():
        # Read from file
        try:
            with open(sync_lyrics_file.get(), 'r', encoding='utf-8') as f:
                lyrics = [line.strip() for line in f.readlines() if line.strip()]
        except:
            messagebox.showerror("Error", "Could not read lyrics file")
            return
    else:
        # Get lyrics from paste area
        text = paste_lyrics_text.get(1.0, tk.END).strip()
        if not text:
            messagebox.showerror("Error", "Please load or paste plain lyrics first")
            return
        
        # Process the pasted text to get clean lyrics lines
        lyrics = []
        for line in text.split('\n'):
            line = line.strip()
            if line:  # Skip empty lines
                lyrics.append(line)
        
        # Double check we have some lyrics
        if not lyrics:
            messagebox.showerror("Error", "No valid lyrics found in the pasted text")
            return
    
    # Show how many lyrics were detected
    update_status(f"Loaded {len(lyrics)} lines of lyrics")
    
    # Get MP3 file
    mp3_path = filedialog.askopenfilename(
        title="Select MP3 File to Sync With",
        filetypes=[("MP3 files", "*.mp3")]
    )
    if not mp3_path:
        return
    
    # Set up synchronization window
    sync_window = tk.Toplevel(root)
    sync_window.title("Sync Lyrics")
    sync_window.geometry("600x500")
    
    # Store data
    sync_data = {
        "lyrics": lyrics,
        "current_index": 0,
        "timestamps": [],
        "mp3_path": mp3_path,
        "start_time": None
    }
    
    # Create UI elements
    instruction_label = ttk.Label(sync_window, text="Press 'Start Sync' to begin, then click 'Mark' or press SPACEBAR each time a line should appear")
    instruction_label.pack(pady=10)
    
    current_lyric = ttk.Label(sync_window, text="", font=("Arial", 16))
    current_lyric.pack(pady=10)
    
    next_lyric = ttk.Label(sync_window, text="", font=("Arial", 12))
    next_lyric.pack(pady=5)
    
    # Create buttons
    button_frame = ttk.Frame(sync_window)
    button_frame.pack(pady=20)
    
    def start_sync():
        """Start synchronization process"""
        # Play the music
        system = platform.system()
        try:
            if system == 'Windows':
                os.startfile(mp3_path)
            elif system == 'Darwin':  # macOS
                subprocess.run(['open', mp3_path])
            else:  # Linux
                subprocess.run(['xdg-open', mp3_path])
        except Exception as e:
            messagebox.showerror("Error", f"Could not play file: {e}")
            return
        
        # Record start time
        sync_data["start_time"] = time.time()
        
        # Update UI
        start_button.config(state='disabled')
        mark_button.config(state='normal')
        
        # Set focus to the window to capture key events
        sync_window.focus_force()
        
        # Show first lyrics
        update_lyric_display()
    
    def mark_timestamp():
        """Mark timestamp for current lyric"""
        if sync_data["start_time"] is None:
            return
            
        # Calculate elapsed time
        elapsed = time.time() - sync_data["start_time"]
        
        # Add timestamp for current lyric
        current_index = sync_data["current_index"]
        timestamp = format_timestamp(elapsed)
        
        if current_index < len(sync_data["lyrics"]):
            sync_data["timestamps"].append((timestamp, sync_data["lyrics"][current_index]))
            
            # Move to next lyric
            sync_data["current_index"] += 1
            
            # Update display
            update_lyric_display()
            
            # Check if we're done
            if sync_data["current_index"] >= len(sync_data["lyrics"]):
                finish_sync()
    
    def update_lyric_display():
        """Update the lyric display"""
        current_index = sync_data["current_index"]
        if current_index < len(sync_data["lyrics"]):
            current_lyric.config(text=sync_data["lyrics"][current_index])
        else:
            current_lyric.config(text="[End of lyrics]")
            
        if current_index + 1 < len(sync_data["lyrics"]):
            next_lyric.config(text=f"Next: {sync_data['lyrics'][current_index + 1]}")
        else:
            next_lyric.config(text="")
    
    def finish_sync():
        """Finish synchronization and save LRC file"""
        # Create LRC content
        lrc_lines = []
        
        # Add metadata
        title = os.path.splitext(os.path.basename(mp3_path))[0]
        lrc_lines.append(f"[ti:{title}]")
        
        # Add synchronized lyrics
        for timestamp, lyric in sync_data["timestamps"]:
            lrc_lines.append(f"{timestamp}{lyric}")
        
        # Save to file
        output_path = os.path.splitext(mp3_path)[0] + ".lrc"
        with open(output_path, 'w', encoding='utf-8') as f:
            for line in lrc_lines:
                f.write(f"{line}\n")
        
        # Show success message
        messagebox.showinfo("Sync Complete", f"LRC file saved to {output_path}")
        
        # Load the file in the main window
        current_file.set(output_path)
        output_text.delete(1.0, tk.END)
        for line in lrc_lines:
            output_text.insert(tk.END, f"{line}\n")
            
        # Close sync window
        sync_window.destroy()
    
    # Bind spacebar to mark timestamp
    def on_key_press(event):
        if event.keysym == "space" and mark_button['state'] != 'disabled':
            mark_timestamp()
    
    sync_window.bind("<KeyPress>", on_key_press)
    
    # Create buttons
    start_button = ttk.Button(button_frame, text="Start Sync", command=start_sync)
    start_button.pack(side=tk.LEFT, padx=10)
    
    mark_button = ttk.Button(button_frame, text="Mark", command=mark_timestamp)
    mark_button.pack(side=tk.LEFT, padx=10)
    mark_button.config(state='disabled')
    
    cancel_button = ttk.Button(button_frame, text="Cancel", command=sync_window.destroy)
    cancel_button.pack(side=tk.LEFT, padx=10)
    
    # Show lyrics list
    lyrics_frame = ttk.Frame(sync_window)
    lyrics_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    ttk.Label(lyrics_frame, text="Lyrics to sync:").pack(anchor=tk.W)
    
    lyrics_display = scrolledtext.ScrolledText(lyrics_frame, width=60, height=15)
    lyrics_display.pack(fill=tk.BOTH, expand=True)
    
    for line in lyrics:
        lyrics_display.insert(tk.END, f"{line}\n")
    lyrics_display.config(state='disabled')

def update_status(message):
    """Update the status label in the GUI"""
    status_label.config(text=message)
    root.update()

def save_lyrics():
    """Save edited lyrics"""
    content = output_text.get(1.0, tk.END)
    if not current_file.get():
        save_path = filedialog.asksaveasfilename(
            defaultextension=".lrc",
            filetypes=[("LRC files", "*.lrc")]
        )
        if not save_path:
            return
        current_file.set(save_path)
    
    with open(current_file.get(), 'w', encoding='utf-8') as f:
        f.write(content)
    
    update_status(f"Lyrics saved to {current_file.get()}")
    messagebox.showinfo("Success", f"Lyrics saved to {current_file.get()}")

def load_lyrics():
    """Load an existing LRC file for editing"""
    lrc_path = filedialog.askopenfilename(
        title="Select LRC File",
        filetypes=[("LRC files", "*.lrc")]
    )
    if not lrc_path:
        return
    
    current_file.set(lrc_path)
    
    with open(lrc_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    output_text.delete(1.0, tk.END)
    output_text.insert(tk.END, content)
    update_status(f"Loaded {lrc_path}")

def load_plain_lyrics():
    """Load plain text lyrics file for syncing"""
    lyrics_path = filedialog.askopenfilename(
        title="Select Lyrics File",
        filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
    )
    if not lyrics_path:
        return
    
    sync_lyrics_file.set(lyrics_path)
    update_status(f"Loaded lyrics from {lyrics_path} for syncing")

def play_music():
    """Open the associated MP3 file in the default player"""
    if not current_file.get():
        messagebox.showerror("Error", "No LRC file loaded")
        return
    
    # Get associated MP3 file
    lrc_path = current_file.get()
    mp3_path = os.path.splitext(lrc_path)[0] + ".mp3"
    
    if not os.path.exists(mp3_path):
        messagebox.showerror("Error", f"MP3 file not found: {mp3_path}")
        return
    
    # Open with default player
    system = platform.system()
    try:
        if system == 'Windows':
            os.startfile(mp3_path)
        elif system == 'Darwin':  # macOS
            subprocess.run(['open', mp3_path])
        else:  # Linux
            subprocess.run(['xdg-open', mp3_path])
        update_status(f"Playing {mp3_path}")
    except Exception as e:
        messagebox.showerror("Error", f"Could not play file: {e}")

def process_file():
    """Handle file selection and processing"""
    mp3_path = filedialog.askopenfilename(
        title="Select MP3 File",
        filetypes=[("MP3 files", "*.mp3")]
    )
    if not mp3_path:
        update_status("No file selected")
        return
    
    output_path = os.path.splitext(mp3_path)[0] + ".lrc"
    current_file.set(output_path)
    
    if online_lyrics_var.get():
        # Try to use online lyrics
        update_status("Searching for lyrics online...")
        result, lines = process_with_online_lyrics(mp3_path, output_path)
    else:
        # Create timestamp template
        interval = float(interval_var.get())
        update_status("Creating timestamps...")
        result, lines = create_timestamp_template(mp3_path, output_path, interval)
    
    output_text.delete(1.0, tk.END)
    if result == "Success":
        if online_lyrics_var.get():
            update_status(f"LRC file created with online lyrics. You can edit and save if needed.")
        else:
            update_status(f"Timestamp template created. Enter your lyrics and save.")
            
        for line in lines:
            output_text.insert(tk.END, f"{line}\n")
    else:
        update_status(result)
        output_text.insert(tk.END, result)

def install_spleeter():
    """Install Spleeter and its dependencies using pip in a separate window"""
    try:
        # Create a new window for installation progress
        install_window = tk.Toplevel()
        install_window.title("Installing Spleeter")
        install_window.geometry("400x300")
        
        # Add progress text widget
        progress_text = scrolledtext.ScrolledText(install_window, width=45, height=15)
        progress_text.pack(padx=10, pady=10)
        
        def update_progress(text):
            progress_text.insert(tk.END, text + "\n")
            progress_text.see(tk.END)
            install_window.update()
        
        update_progress("Installing Spleeter and required dependencies...")
        update_progress("This may take several minutes...")
        
        # Use a list to store the process
        process = None
        
        def run_install():
            nonlocal process
            try:
                # Create a temporary batch file for installation
                temp_dir = tempfile.gettempdir()
                batch_file = os.path.join(temp_dir, "install_spleeter.bat")
                
                with open(batch_file, 'w') as f:
                    f.write("@echo off\n")
                    f.write("pip install spleeter\n")
                    f.write("pause\n")
                
                # Run the batch file in a new window
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
                process = subprocess.Popen(
                    batch_file,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True,
                    startupinfo=startupinfo
                )
                
                # Wait for completion
                stdout, stderr = process.communicate()
                
                if process.returncode == 0:
                    update_progress("\nInstallation completed successfully!")
                    messagebox.showinfo("Success", "Spleeter has been installed successfully.\nPlease restart the application.")
                    install_window.destroy()
                else:
                    update_progress("\nError during installation:")
                    update_progress(stderr)
                    messagebox.showerror("Installation Error", 
                        "Failed to install Spleeter. Please try installing manually:\n"
                        "1. Open Command Prompt as Administrator\n"
                        "2. Run: pip install spleeter")
                
            except Exception as e:
                update_progress(f"\nError: {str(e)}")
                messagebox.showerror("Error", f"Installation failed: {str(e)}")
            finally:
                # Clean up
                try:
                    if os.path.exists(batch_file):
                        os.remove(batch_file)
                except:
                    pass
        
        # Run installation in a separate thread
        install_thread = threading.Thread(target=run_install)
        install_thread.daemon = True
        install_thread.start()
        
        def check_thread():
            if install_thread.is_alive():
                install_window.after(100, check_thread)
            else:
                if process and process.returncode != 0:
                    update_progress("\nInstallation failed. Please check the error messages above.")
        
        check_thread()
        
    except Exception as e:
        messagebox.showerror("Error", f"Failed to start installation: {str(e)}")
        return False
    
    return True

def remove_vocals_with_spleeter(mp3_path):
    """Remove vocals using Spleeter with enhanced settings"""
    try:
        # Check if spleeter is installed
        try:
            import spleeter
            from spleeter.separator import Separator
        except ImportError:
            result = messagebox.askyesno("Install Spleeter", 
                "Spleeter is required for better vocal removal. Would you like to install it now?\n\n"
                "This will install:\n"
                "- spleeter\n"
                "- tensorflow\n\n"
                "The installation may take a few minutes.")
            
            if result:
                if not install_spleeter():
                    return "Installation cancelled", None
                return "Please restart the application to use Spleeter", None
            else:
                return "Cancelled: Spleeter installation required", None

        update_status("Loading Spleeter model (this may take a minute)...")
        
        # Create a separator instance with better quality settings
        separator = Separator('spleeter:4stems-16kHz',
                            multiprocess=False,  # More stable on Windows
                            stft_backend='tensorflow',  # Better quality
                            mask_type='soft')  # Better separation
        
        # Create temporary directory for processing
        temp_dir = os.path.join(tempfile.gettempdir(), "spleeter_output")
        os.makedirs(temp_dir, exist_ok=True)
        
        update_status("Separating audio (this may take several minutes)...")
        
        # Separate the audio with higher quality settings
        separator.separate_to_file(mp3_path, temp_dir, 
                                 codec='wav',
                                 bitrate='320k',
                                 duration=None,  # Process entire file
                                 offset=0)
        
        # Get the paths for different stems
        filename = os.path.splitext(os.path.basename(mp3_path))[0]
        base_path = os.path.join(temp_dir, filename)
        accompaniment_path = os.path.join(base_path, "accompaniment.wav")
        bass_path = os.path.join(base_path, "bass.wav")
        drums_path = os.path.join(base_path, "drums.wav")
        other_path = os.path.join(base_path, "other.wav")
        
        if not all(os.path.exists(p) for p in [accompaniment_path, bass_path, drums_path, other_path]):
            return "Error: Separation failed", None
            
        # Combine all non-vocal stems with adjusted volumes
        update_status("Mixing stems for optimal karaoke...")
        try:
            accompaniment = AudioSegment.from_wav(accompaniment_path)
            bass = AudioSegment.from_wav(bass_path)
            drums = AudioSegment.from_wav(drums_path)
            other = AudioSegment.from_wav(other_path)
            
            # Adjust volumes for better mix
            bass = bass + 2  # Boost bass slightly
            drums = drums - 1  # Reduce drums slightly
            other = other + 1  # Boost other slightly
            
            # Mix all stems
            final_mix = accompaniment.overlay(bass)
            final_mix = final_mix.overlay(drums)
            final_mix = final_mix.overlay(other)
            
            # Apply some mastering
            final_mix = final_mix.normalize()  # Normalize volume
            
            # Export final mix
            output_path = os.path.splitext(mp3_path)[0] + "_karaoke_spleeter.mp3"
            final_mix.export(output_path, format="mp3", bitrate="320k")
            
        except Exception as e:
            print(f"Error mixing stems: {e}")
            # Fallback to just using accompaniment if mixing fails
            output_path = os.path.splitext(mp3_path)[0] + "_karaoke_spleeter.mp3"
            AudioSegment.from_wav(accompaniment_path).export(output_path, format="mp3", bitrate="320k")
        
        # Clean up temp files
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
        
        return "Success", output_path
        
    except Exception as e:
        return f"Error: {e}", None

def remove_vocals(mp3_path):
    """Remove vocals from an MP3 file"""
    
    # Ask user which method to use
    choice = messagebox.askyesno("Vocal Removal Method", 
        "Would you like to use Spleeter for high-quality vocal removal?\n\n"
        "Yes = Use Spleeter (recommended, requires installation)\n"
        "No = Use basic removal (faster but less effective)")
    
    if choice:
        # Use Spleeter
        return remove_vocals_with_spleeter(mp3_path)
    else:
        # Use existing basic method
        return remove_vocals_basic(mp3_path)

def remove_vocals_basic(mp3_path):
    """Basic vocal removal using phase cancellation (original method)"""
    # ... existing remove_vocals code here ...
    # (keep the original implementation but rename it)

def create_karaoke_video():
    """Create a karaoke video with lyrics and backing track"""
    # Choose MP3 file
    mp3_path = filedialog.askopenfilename(
        title="Select MP3 File",
        filetypes=[("MP3 files", "*.mp3")]
    )
    if not mp3_path:
        update_status("No file selected")
        return
    
    # Check if we already have lyrics
    lrc_path = os.path.splitext(mp3_path)[0] + ".lrc"
    if not os.path.exists(lrc_path):
        # Ask if user wants to create lyrics now
        if messagebox.askyesno("No Lyrics Found", 
                               "No LRC file found for this MP3. Do you want to create one now?"):
            # Go to lyrics creation tab
            tab_control.select(0)  # Select the first tab (lyrics creation)
            current_file.set("")  # Clear current file
            process_file()  # Start the lyrics creation process
            return
        else:
            update_status("Karaoke video creation cancelled")
            return
    
    # Ask if user wants to remove vocals
    if messagebox.askyesno("Vocal Removal", 
                          "Do you want to remove vocals from the MP3?"):
        update_status("Removing vocals...")
        result, karaoke_path = remove_vocals(mp3_path)
        if "Error" in result:
            messagebox.showerror("Error", result)
            return
        # Use the karaoke version for the video
        audio_path = karaoke_path
    else:
        # Use original audio
        audio_path = mp3_path
    
    # Ask for video output path
    video_path = filedialog.asksaveasfilename(
        title="Save Karaoke Video As",
        defaultextension=".mp4",
        filetypes=[("MP4 files", "*.mp4")]
    )
    if not video_path:
        update_status("Video creation cancelled")
        return
    
    try:
        # Check if moviepy is installed, if not suggest installing it
        try:
            from moviepy.editor import (VideoClip, AudioFileClip, TextClip, 
                                       CompositeVideoClip, ColorClip)
            from moviepy.video.io.VideoFileClip import VideoFileClip
        except ImportError:
            messagebox.showerror("Missing Library", 
                                "MoviePy is required for video creation.\n\n"
                                "Please install it using:\n"
                                "pip install moviepy")
            return
        
        # Check if ImageMagick is configured
        if not moviepy_configured:
            # Try one more time to configure it
            setup_moviepy()
            
            # If still not configured, show detailed instructions
            if not moviepy_configured:
                messagebox.showerror("ImageMagick Not Found", 
                                    "ImageMagick is required for creating videos with text.\n\n"
                                    "Please follow these steps:\n"
                                    "1. Download and install ImageMagick from https://imagemagick.org/script/download.php\n"
                                    "2. During installation, ensure 'Add to system PATH' is checked\n"
                                    "3. Restart this application after installation\n\n"
                                    "For advanced configuration:\n"
                                    "1. Add this to your Python code before importing MoviePy:\n"
                                    "   from moviepy.config import change_settings\n"
                                    "   change_settings({'IMAGEMAGICK_BINARY': path/to/magick.exe})")
                return
        
        # Try to check if ImageMagick is working
        try:
            from moviepy.config import get_setting
            magick_binary = get_setting("IMAGEMAGICK_BINARY")
            
            if magick_binary:
                # Try to run a simple ImageMagick command
                subprocess.check_output([magick_binary, "-version"])
            else:
                # Use default command
                subprocess.check_output(["magick", "-version"])
        except Exception as e:
            messagebox.showerror("ImageMagick Error", 
                                f"ImageMagick found but not working correctly: {e}\n\n"
                                "Please make sure ImageMagick is properly installed.")
            return
        
        # Parse LRC file
        with open(lrc_path, 'r', encoding='utf-8') as f:
            lrc_content = f.readlines()
        
        # Display raw content for debugging
        print("Raw LRC content:")
        for i, line in enumerate(lrc_content):
            print(f"{i}: {line.strip()}")
        
        # Extract lyrics and timestamps
        lyrics = []
        metadata = {}
        
        for line in lrc_content:
            line = line.strip()
            if not line:
                continue
                
            # Check for metadata
            if line.startswith('[ti:'):
                metadata['title'] = line[4:-1]
            elif line.startswith('[ar:'):
                metadata['artist'] = line[4:-1]
            elif line.startswith('[length:'):
                metadata['length'] = line[8:-1]
            # Extract lyrics with timestamps
            elif '[' in line and ']' in line:
                # Try multiple timestamp formats and lyric layouts
                timestamp_end = line.find(']') + 1
                timestamp = line[1:timestamp_end-1]  # Remove brackets
                lyric_text = line[timestamp_end:].strip()
                
                # Skip placeholder lyrics or empty lyrics
                if lyric_text == "[Enter lyrics here]" or not lyric_text:
                    continue
                    
                # Convert timestamp to seconds
                try:
                    if ':' in timestamp:
                        minutes, seconds = timestamp.split(':')
                        try:
                            # Try standard format with minutes and decimal seconds
                            total_seconds = float(minutes) * 60 + float(seconds)
                            lyrics.append((total_seconds, lyric_text))
                        except ValueError:
                            # Handle other possible time formats
                            print(f"Warning: Non-standard timestamp format: {timestamp}")
                            
                            # Try mm:ss:xx format
                            try:
                                parts = timestamp.split(':')
                                if len(parts) == 3:  # mm:ss:xx format
                                    minutes, seconds, frames = parts
                                    total_seconds = (float(minutes) * 60 + 
                                                  float(seconds) + 
                                                  float(frames) / 100)
                                    lyrics.append((total_seconds, lyric_text))
                                else:
                                    print(f"Unknown time format with {len(parts)} parts")
                            except Exception as nested_e:
                                print(f"Failed to parse alternative format: {nested_e}")
                    else:
                        # Try to interpret it as seconds
                        try:
                            total_seconds = float(timestamp)
                            lyrics.append((total_seconds, lyric_text))
                        except ValueError:
                            print(f"Warning: Non-standard timestamp not parseable: {timestamp}")
                except ValueError as e:
                    # Log the error for debugging
                    print(f"Error parsing timestamp '{timestamp}': {e}")
                    # Skip invalid timestamps
                    continue
        
        # Print detected lyrics for debugging
        print(f"Detected {len(lyrics)} valid lyrics lines:")
        for i, (time, text) in enumerate(lyrics[:5]):
            print(f"{i}: {format_timestamp(time)} - {text}")
        if len(lyrics) > 5:
            print("...")
        
        # Sort lyrics by timestamp
        lyrics.sort(key=lambda x: x[0])
        
        # Make sure we have actual lyrics to display
        if not lyrics:
            # Show the actual contents of the file for debugging
            error_message = "No usable lyrics found in the LRC file.\n\n"
            
            # Add debugging info
            error_message += "File contents preview:\n"
            preview_lines = min(10, len(lrc_content))
            for i in range(preview_lines):
                if i < len(lrc_content):
                    error_message += f"{lrc_content[i].strip()}\n"
            
            error_message += "\nPlease make sure your LRC file contains proper timestamps\n"
            error_message += "in the format [mm:ss.xx] followed by lyrics text."
            
            messagebox.showerror("No Lyrics Found", error_message)
            return
        
        # Get audio duration
        audio = AudioSegment.from_mp3(audio_path)
        audio_duration = audio.duration_seconds
        
        # Setup moviepy objects
        audio_clip = AudioFileClip(audio_path)
        
        # Video settings
        fps = 30
        width, height = 1280, 720
        duration = audio_clip.duration
        
        update_status("Creating video background...")
        
        # Create background - a gradient or solid color
        def make_gradient_background(size, t):
            """Create a gradient background that slowly shifts colors over time"""
            w, h = size
            x = np.linspace(0, 1, w)
            y = np.linspace(0, 1, h)
            
            # Create meshgrid for coordinates
            X, Y = np.meshgrid(x, y)
            
            # Create a smooth time-varying gradient
            r = np.sin(X * 3 + t * 0.1) * 0.1 + 0.1
            g = np.sin(Y * 3 + t * 0.15) * 0.1 + 0.1 
            b = np.sin((X + Y) * 3 + t * 0.2) * 0.1 + 0.3
            
            # Stack RGB channels
            return np.dstack([r, g, b])
        
        # Create background clip
        background_clip = VideoClip(lambda t: make_gradient_background((width, height), t) * 255, 
                                  duration=duration)
        
        update_status("Processing lyrics for video...")
        
        # Font settings - use a more widely available font
        font = "Arial" if platform.system() == "Windows" else None  # Use default if not Windows
        fontsize = 36
        font_color = "white"
        current_line_color = "#00FFFF"  # cyan for current line
        
        # Create lyric clips
        lyric_clips = []
        
        # Title card at the beginning
        title_text = metadata.get('title', os.path.basename(mp3_path))
        artist_text = metadata.get('artist', '')
        
        if artist_text:
            title_display = f"{title_text}\nby {artist_text}"
        else:
            title_display = title_text
        
        # Use simpler text rendering if having issues with TextClip  
        try:    
            title_clip = TextClip(title_display, fontsize=48, font=font, color=font_color,
                                size=(width-100, None), method='caption', align='center')
            title_clip = title_clip.set_position('center').set_duration(3).set_start(0)
            lyric_clips.append(title_clip)
            
            # Countdown 3-2-1
            for i in range(3, 0, -1):
                countdown = TextClip(str(i), fontsize=120, font=font, color=font_color)
                countdown = countdown.set_position('center').set_duration(1).set_start(3+(3-i))
                lyric_clips.append(countdown)
            
            # Process each lyric line for display
            for i in range(len(lyrics)):
                current_time, current_text = lyrics[i]
                
                # Determine duration until next lyric
                if i < len(lyrics) - 1:
                    next_time = lyrics[i+1][0]
                    duration = next_time - current_time
                else:
                    # Last lyric - show until end
                    duration = audio_duration - current_time
                
                # Create text clip for current lyric
                if current_text:  # Only create clip if there's actual text
                    text_clip = TextClip(current_text, fontsize=fontsize, font=font, 
                                      color=current_line_color, size=(width-100, None), 
                                      method='caption', align='center')
                    text_clip = text_clip.set_position('center').set_duration(duration).set_start(current_time)
                    lyric_clips.append(text_clip)
                
                # Show previous and next lines (more muted)
                if i > 0:  # Previous line
                    prev_time, prev_text = lyrics[i-1]
                    if prev_text:
                        prev_clip = TextClip(prev_text, fontsize=fontsize-6, font=font, 
                                          color=font_color, size=(width-100, None), 
                                          method='caption', align='center')
                        prev_clip = prev_clip.set_position(('center', 280)).set_duration(duration).set_start(current_time)
                        prev_clip = prev_clip.set_opacity(0.7)  # More transparent
                        lyric_clips.append(prev_clip)
                
                if i < len(lyrics) - 1:  # Next line
                    next_time, next_text = lyrics[i+1]
                    if next_text:
                        next_clip = TextClip(next_text, fontsize=fontsize-6, font=font, 
                                          color=font_color, size=(width-100, None), 
                                          method='caption', align='center') 
                        next_clip = next_clip.set_position(('center', 440)).set_duration(duration).set_start(current_time)
                        next_clip = next_clip.set_opacity(0.7)  # More transparent
                        lyric_clips.append(next_clip)
        except Exception as text_error:
            # If text rendering fails, try with simpler method
            messagebox.showwarning("Text Rendering Issue", 
                                 f"Advanced text rendering failed: {text_error}\n\nTrying simpler method...")
            
            # Clear existing clips and try with basic text rendering
            lyric_clips = []
            
            # Simple title
            title_clip = TextClip(title_display, fontsize=48, font=font, color=font_color)
            title_clip = title_clip.set_position('center').set_duration(3).set_start(0)
            lyric_clips.append(title_clip)
            
            # Process each lyric line in simplified way
            for i in range(len(lyrics)):
                current_time, current_text = lyrics[i]
                
                if i < len(lyrics) - 1:
                    next_time = lyrics[i+1][0]
                    duration = next_time - current_time
                else:
                    duration = audio_duration - current_time
                
                if current_text:
                    text_clip = TextClip(current_text, fontsize=fontsize, font=font, color=font_color)
                    text_clip = text_clip.set_position('center').set_duration(duration).set_start(current_time)
                    lyric_clips.append(text_clip)
        
        update_status("Compositing video...")
        
        # Combine all clips
        video = CompositeVideoClip([background_clip] + lyric_clips)
        
        # Add audio
        video = video.set_audio(audio_clip)
        
        # Write video file
        update_status("Rendering karaoke video...")
        video.write_videofile(video_path, fps=fps, codec='libx264', 
                             audio_codec='aac', threads=4)
        
        update_status("Karaoke video created successfully!")
        messagebox.showinfo("Success", f"Karaoke video created: {video_path}")
        
    except Exception as e:
        error_msg = str(e)
        update_status(f"Error creating video: {error_msg}")
        messagebox.showerror("Error", f"Failed to create video: {error_msg}")
        
        # Provide more specific guidance based on error message
        if "imagemagick" in error_msg.lower() or "magick" in error_msg.lower():
            messagebox.showinfo("ImageMagick Issue", 
                            "This error is related to ImageMagick configuration.\n\n"
                            "1. Download and install ImageMagick from:\n"
                            "   https://imagemagick.org/script/download.php\n\n"
                            "2. During installation, make sure to select:\n"
                            "   - Install legacy utilities\n"
                            "   - Add application directory to your system path\n\n"
                            "3. Restart this application after installation")
        elif "moviepy" in error_msg.lower() or "import" in error_msg.lower():
            messagebox.showinfo("Dependency Issue", 
                            "This feature requires additional libraries:\n\n"
                            "pip install moviepy numpy")
        return

def display_lrc_preview():
    """Display a preview of the LRC file in the output text area"""
    if not current_file.get() or not os.path.exists(current_file.get()):
        messagebox.showinfo("No LRC File", "Please load or create an LRC file first")
        return
        
    # Read the LRC file
    with open(current_file.get(), 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract and parse lyrics
    lines = content.split('\n')
    metadata_lines = []
    lyric_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if line.startswith('[ti:') or line.startswith('[ar:') or line.startswith('[length:'):
            metadata_lines.append(line)
        elif '[' in line and ']' in line:
            lyric_lines.append(line)
    
    # Clear the output text
    output_text.delete(1.0, tk.END)
    
    # Display metadata
    output_text.insert(tk.END, "== LRC File Preview ==\n\n")
    if metadata_lines:
        output_text.insert(tk.END, "Metadata:\n")
        for line in metadata_lines:
            output_text.insert(tk.END, f"{line}\n")
        output_text.insert(tk.END, "\n")
    
    # Display lyrics count
    output_text.insert(tk.END, f"Total lyrics lines: {len(lyric_lines)}\n\n")
    
    # Display a sample of lyrics
    if lyric_lines:
        output_text.insert(tk.END, "Sample lyrics:\n")
        sample_size = min(10, len(lyric_lines))
        for i in range(sample_size):
            output_text.insert(tk.END, f"{lyric_lines[i]}\n")
        
        if len(lyric_lines) > sample_size:
            output_text.insert(tk.END, "...\n")
            output_text.insert(tk.END, f"{lyric_lines[-1]}\n")
    
    # Update status
    update_status(f"Previewing LRC file: {current_file.get()}")

def fix_lrc_file():
    """Fix the current LRC file by ensuring all timestamps are properly formatted"""
    if not current_file.get() or not os.path.exists(current_file.get()):
        messagebox.showinfo("No LRC File", "Please load or create an LRC file first")
        return
    
    try:
        # Read the LRC file
        with open(current_file.get(), 'r', encoding='utf-8') as f:
            lrc_content = f.readlines()
        
        # Process the content to fix timestamps and format
        fixed_lines = []
        lyrics_fixed = 0
        
        for line in lrc_content:
            line = line.strip()
            if not line:
                fixed_lines.append("")
                continue
            
            # Keep metadata lines as is
            if line.startswith('[ti:') or line.startswith('[ar:') or line.startswith('[length:'):
                fixed_lines.append(line)
                continue
            
            # Fix timestamp format if needed
            if '[' in line and ']' in line:
                timestamp_end = line.find(']') + 1
                timestamp = line[1:timestamp_end-1]  # Remove brackets
                lyric_text = line[timestamp_end:].strip()
                
                # Try to fix any timestamp format issues
                try:
                    if ':' in timestamp:
                        # Standard format - just verify and reformat
                        minutes, seconds = timestamp.split(':')
                        minutes = int(float(minutes))
                        seconds = float(seconds)
                        
                        # Fix any out-of-bounds values
                        if seconds >= 60:
                            minutes += int(seconds / 60)
                            seconds = seconds % 60
                        
                        # Create proper timestamp
                        fixed_timestamp = f"[{minutes:02d}:{seconds:05.2f}]"
                        fixed_lines.append(f"{fixed_timestamp}{lyric_text}")
                        lyrics_fixed += 1
                    else:
                        # Non-standard format - try to interpret it
                        # For now, just preserve the original line
                        fixed_lines.append(line)
                except Exception:
                    # If we can't fix it, preserve the original
                    fixed_lines.append(line)
            else:
                # Not a lyric line with timestamp, preserve as is
                fixed_lines.append(line)
        
        # Save the fixed content
        backup_path = current_file.get() + ".bak"
        with open(backup_path, 'w', encoding='utf-8') as f:
            for line in lrc_content:
                f.write(f"{line}")
        
        # Write the fixed content
        with open(current_file.get(), 'w', encoding='utf-8') as f:
            for line in fixed_lines:
                f.write(f"{line}\n")
        
        # Update the UI
        output_text.delete(1.0, tk.END)
        for line in fixed_lines:
            output_text.insert(tk.END, f"{line}\n")
        
        # Show success message
        if lyrics_fixed > 0:
            messagebox.showinfo("LRC Fixed", 
                             f"Fixed {lyrics_fixed} lyrics lines.\n"
                             f"Original file backed up to {backup_path}")
        else:
            messagebox.showinfo("LRC File", "No timestamp fixes needed.")
            
        update_status(f"LRC file fixed: {current_file.get()}")
        
    except Exception as e:
        messagebox.showerror("Error", f"Failed to fix LRC file: {e}")

def force_create_video():
    """Create karaoke video by directly parsing the LRC text from the editor"""
    if not current_file.get():
        messagebox.showinfo("No LRC File", "Please load an LRC file first")
        return
        
    # Get the content directly from the text editor
    lrc_content = output_text.get(1.0, tk.END).splitlines()
    
    # Strip empty lines and whitespace
    lrc_content = [line.strip() for line in lrc_content if line.strip()]
    
    # Get associated MP3 file
    lrc_path = current_file.get()
    mp3_path = os.path.splitext(lrc_path)[0] + ".mp3"
    
    if not os.path.exists(mp3_path):
        # Allow the user to select an MP3 file
        mp3_path = filedialog.askopenfilename(
            title="Select MP3 File",
            filetypes=[("MP3 files", "*.mp3")]
        )
        if not mp3_path:
            update_status("No MP3 file selected")
            return
            
    # Ask if user wants to remove vocals
    if messagebox.askyesno("Vocal Removal", 
                          "Do you want to remove vocals from the MP3?"):
        update_status("Removing vocals...")
        result, karaoke_path = remove_vocals(mp3_path)
        if "Error" in result:
            messagebox.showerror("Error", result)
            return
        # Use the karaoke version for the video
        audio_path = karaoke_path
    else:
        # Use original audio
        audio_path = mp3_path
    
    # Ask for video output path
    video_path = filedialog.asksaveasfilename(
        title="Save Karaoke Video As",
        defaultextension=".mp4",
        filetypes=[("MP4 files", "*.mp4")]
    )
    if not video_path:
        update_status("Video creation cancelled")
        return
    
    try:
        # Check if moviepy is installed
        try:
            from moviepy.editor import (VideoClip, AudioFileClip, TextClip, 
                                       CompositeVideoClip, ColorClip)
            from moviepy.video.io.VideoFileClip import VideoFileClip
        except ImportError:
            messagebox.showerror("Missing Library", 
                                "MoviePy is required for video creation.\n\n"
                                "Please install it using:\n"
                                "pip install moviepy")
            return
            
        # Check if ImageMagick is configured
        if not moviepy_configured:
            # Try one more time to configure it
            setup_moviepy()
            
            # If still not configured, show detailed instructions
            if not moviepy_configured:
                messagebox.showerror("ImageMagick Not Found", 
                                    "ImageMagick is required for creating videos with text.\n\n"
                                    "Please follow these steps:\n"
                                    "1. Download and install ImageMagick from https://imagemagick.org/script/download.php\n"
                                    "2. During installation, ensure 'Add to system PATH' is checked\n"
                                    "3. Restart this application after installation")
                return
                
        # Parse LRC content manually
        lyrics = []
        metadata = {}
        
        for line in lrc_content:
            # Check for metadata
            if line.startswith('[ti:'):
                metadata['title'] = line[4:-1]
            elif line.startswith('[ar:'):
                metadata['artist'] = line[4:-1]
            elif line.startswith('[length:'):
                metadata['length'] = line[8:-1]
            # Extract lyrics with timestamps - direct matching
            elif line.startswith('[') and ']' in line:
                timestamp_end = line.find(']') + 1
                timestamp = line[1:timestamp_end-1]  # Remove brackets
                lyric_text = line[timestamp_end:].strip()
                
                # Skip empty lyrics
                if not lyric_text:
                    continue
                    
                # Parse timestamp directly
                try:
                    minutes, seconds = timestamp.split(':')
                    total_seconds = float(minutes) * 60 + float(seconds)
                    lyrics.append((total_seconds, lyric_text))
                except Exception as e:
                    print(f"Skipping line with invalid timestamp: {line} - {e}")
        
        # Make sure we have lyrics
        if not lyrics:
            messagebox.showerror("Error", "No valid lyrics found in the editor")
            return
            
        # Sort lyrics by timestamp
        lyrics.sort(key=lambda x: x[0])
        
        # Set up for video creation
        # Get audio duration
        audio = AudioSegment.from_mp3(audio_path)
        audio_duration = audio.duration_seconds
        
        # Setup moviepy objects
        audio_clip = AudioFileClip(audio_path)
        
        # Video settings
        fps = 30
        width, height = 1280, 720
        duration = audio_clip.duration
        
        update_status("Creating video background...")
        
        # Create background - a gradient or solid color
        def make_gradient_background(size, t):
            """Create a gradient background that slowly shifts colors over time"""
            w, h = size
            x = np.linspace(0, 1, w)
            y = np.linspace(0, 1, h)
            
            # Create meshgrid for coordinates
            X, Y = np.meshgrid(x, y)
            
            # Create a smooth time-varying gradient
            r = np.sin(X * 3 + t * 0.1) * 0.1 + 0.1
            g = np.sin(Y * 3 + t * 0.15) * 0.1 + 0.1 
            b = np.sin((X + Y) * 3 + t * 0.2) * 0.1 + 0.3
            
            # Stack RGB channels
            return np.dstack([r, g, b])
        
        # Create background clip
        background_clip = VideoClip(lambda t: make_gradient_background((width, height), t) * 255, 
                                  duration=duration)
        
        update_status("Processing lyrics for video...")
        
        # Font settings - use a more widely available font
        font = "Arial" if platform.system() == "Windows" else None  # Use default if not Windows
        fontsize = 36
        font_color = "white"
        current_line_color = "#00FFFF"  # cyan for current line
        
        # Create lyric clips
        lyric_clips = []
        
        # Title card at the beginning
        title_text = metadata.get('title', os.path.basename(mp3_path))
        artist_text = metadata.get('artist', '')
        
        if artist_text:
            title_display = f"{title_text}\nby {artist_text}"
        else:
            title_display = title_text
            
        # Use simpler approach for all text rendering to avoid problems
        try:
            # Title
            title_clip = TextClip(title_display, fontsize=48, font=font, color=font_color)
            title_clip = title_clip.set_position('center').set_duration(3).set_start(0)
            lyric_clips.append(title_clip)
            
            # Countdown 3-2-1
            for i in range(3, 0, -1):
                countdown = TextClip(str(i), fontsize=120, font=font, color=font_color)
                countdown = countdown.set_position('center').set_duration(1).set_start(3+(3-i))
                lyric_clips.append(countdown)
                
            # Process lyrics without fancy formatting
            for i in range(len(lyrics)):
                current_time, current_text = lyrics[i]
                
                # Determine duration
                if i < len(lyrics) - 1:
                    next_time = lyrics[i+1][0]
                    duration = next_time - current_time
                else:
                    duration = audio_duration - current_time
                
                # Create simple text clip
                text_clip = TextClip(current_text, fontsize=fontsize, font=font, color=current_line_color)
                text_clip = text_clip.set_position('center').set_duration(duration).set_start(current_time)
                lyric_clips.append(text_clip)
        
        except Exception as e:
            messagebox.showerror("Text Rendering Error", f"Error creating text: {e}")
            return
            
        update_status("Compositing video...")
        
        # Combine all clips
        video = CompositeVideoClip([background_clip] + lyric_clips)
        
        # Add audio
        video = video.set_audio(audio_clip)
        
        # Write video file
        update_status("Rendering karaoke video...")
        video.write_videofile(video_path, fps=fps, codec='libx264', 
                             audio_codec='aac', threads=4)
        
        update_status("Karaoke video created successfully!")
        messagebox.showinfo("Success", f"Karaoke video created: {video_path}")
    
    except Exception as e:
        error_msg = str(e)
        update_status(f"Error creating video: {error_msg}")
        messagebox.showerror("Error", f"Failed to create video: {error_msg}")

# Set up GUI
root = tk.Tk()
root.title("Karaoke Maker")
root.geometry("800x600")

# Variable to store current file path
current_file = tk.StringVar()
sync_lyrics_file = tk.StringVar()

# Settings variables
interval_var = tk.StringVar(value="2")
online_lyrics_var = tk.BooleanVar(value=True)  # Default to online lyrics

# Create main frame
main_frame = ttk.Frame(root, padding="10")
main_frame.pack(fill=tk.BOTH, expand=True)

# Create tabs
tab_control = ttk.Notebook(main_frame)
tab_control.pack(fill=tk.BOTH, expand=True)

# Create tabs
lyrics_tab = ttk.Frame(tab_control)
sync_tab = ttk.Frame(tab_control)
karaoke_tab = ttk.Frame(tab_control)

tab_control.add(lyrics_tab, text="Lyrics Creation")
tab_control.add(sync_tab, text="Manual Sync")
tab_control.add(karaoke_tab, text="Karaoke Video")

# === Lyrics Creation Tab ===
# Settings frame
settings_frame = ttk.LabelFrame(lyrics_tab, text="Settings")
settings_frame.pack(fill=tk.X, pady=5)

# Online lyrics settings
online_frame = ttk.Frame(settings_frame)
online_frame.pack(fill=tk.X, pady=5)

online_lyrics_check = ttk.Checkbutton(online_frame, 
    text="Search for lyrics online (recommended - tries LRCLib first for synced lyrics)", 
    variable=online_lyrics_var)
online_lyrics_check.pack(side=tk.LEFT, padx=5)

# Interval setting (only used if not using online lyrics)
interval_frame = ttk.Frame(settings_frame)
interval_frame.pack(fill=tk.X, pady=5)

ttk.Label(interval_frame, text="Time interval if creating manual timestamps:").pack(side=tk.LEFT, padx=5)
interval_combo = ttk.Combobox(interval_frame, textvariable=interval_var, width=5)
interval_combo['values'] = ("1", "2", "3", "5", "10")
interval_combo.pack(side=tk.LEFT, padx=5)

# Create button frame
button_frame = ttk.Frame(lyrics_tab)
button_frame.pack(pady=5, fill=tk.X)

process_button = ttk.Button(button_frame, text="Create LRC File", command=process_file)
process_button.pack(side=tk.LEFT, padx=5)

load_button = ttk.Button(button_frame, text="Load LRC File", command=load_lyrics)
load_button.pack(side=tk.LEFT, padx=5)

save_button = ttk.Button(button_frame, text="Save LRC File", command=save_lyrics)
save_button.pack(side=tk.LEFT, padx=5)

# Instructions
instruction_frame = ttk.Frame(lyrics_tab)
instruction_frame.pack(fill=tk.X, pady=5)
ttk.Label(instruction_frame, text="1. Make sure your MP3 filename is formatted as 'Artist - Title.mp3' for best results").pack(anchor=tk.W)
ttk.Label(instruction_frame, text="2. Click 'Create LRC File' to search for lyrics online and align them with the song").pack(anchor=tk.W)
ttk.Label(instruction_frame, text="3. Edit the lyrics and timing if needed").pack(anchor=tk.W)
ttk.Label(instruction_frame, text="4. Save when finished").pack(anchor=tk.W)

# === Manual Sync Tab ===
sync_frame = ttk.Frame(sync_tab, padding=10)
sync_frame.pack(fill=tk.BOTH, expand=True)

ttk.Label(sync_frame, text="Manual Synchronization", font=("Arial", 14, "bold")).pack(anchor=tk.W, pady=10)

ttk.Label(sync_frame, text="This mode lets you create perfectly synchronized LRC files by clicking as each line is sung:").pack(anchor=tk.W)

sync_instructions = ttk.Frame(sync_frame)
sync_instructions.pack(fill=tk.X, pady=10)

ttk.Label(sync_instructions, text="1. Load a lyrics file OR paste lyrics directly below (one line per line)").pack(anchor=tk.W)
ttk.Label(sync_instructions, text="2. Click 'Start Sync Mode' and select your MP3 file").pack(anchor=tk.W)
ttk.Label(sync_instructions, text="3. When the music starts, click 'Mark' or press SPACEBAR each time a line should appear").pack(anchor=tk.W)
ttk.Label(sync_instructions, text="4. The synchronized LRC file will be created automatically").pack(anchor=tk.W)

# Add paste area for lyrics
ttk.Label(sync_frame, text="Paste lyrics here (one line per line):").pack(anchor=tk.W, pady=(10, 5))
paste_lyrics_text = scrolledtext.ScrolledText(sync_frame, width=60, height=10)
paste_lyrics_text.pack(fill=tk.X, pady=5)

sync_button_frame = ttk.Frame(sync_frame)
sync_button_frame.pack(pady=15)

load_lyrics_btn = ttk.Button(sync_button_frame, text="Load Lyrics File", command=load_plain_lyrics)
load_lyrics_btn.pack(side=tk.LEFT, padx=10)

clear_button = ttk.Button(sync_button_frame, text="Clear", command=lambda: paste_lyrics_text.delete(1.0, tk.END))
clear_button.pack(side=tk.LEFT, padx=10)

start_sync_btn = ttk.Button(sync_button_frame, text="Start Sync Mode", command=enter_sync_mode)
start_sync_btn.pack(side=tk.LEFT, padx=10)

# === Karaoke Video Tab ===
karaoke_frame = ttk.Frame(karaoke_tab, padding=10)
karaoke_frame.pack(fill=tk.BOTH, expand=True)

ttk.Label(karaoke_frame, text="Karaoke Video Creation", font=("Arial", 14, "bold")).pack(anchor=tk.W, pady=10)

ttk.Label(karaoke_frame, text="Create karaoke videos with synchronized lyrics and optional vocal removal:").pack(anchor=tk.W)

karaoke_instructions = ttk.Frame(karaoke_frame)
karaoke_instructions.pack(fill=tk.X, pady=10)

ttk.Label(karaoke_instructions, text="1. Create or load an LRC file first (in the Lyrics Creation tab)").pack(anchor=tk.W)
ttk.Label(karaoke_instructions, text="2. Click 'Create Karaoke Video' and select your MP3 file").pack(anchor=tk.W)
ttk.Label(karaoke_instructions, text="3. Choose whether to remove vocals").pack(anchor=tk.W)
ttk.Label(karaoke_instructions, text="4. Save your video file").pack(anchor=tk.W)

# Create Karaoke button
karaoke_button_frame = ttk.Frame(karaoke_frame)
karaoke_button_frame.pack(pady=15)

load_lrc_btn = ttk.Button(karaoke_button_frame, text="Load LRC File", command=load_lyrics)
load_lrc_btn.pack(side=tk.LEFT, padx=10)

preview_lrc_btn = ttk.Button(karaoke_button_frame, text="Preview LRC", command=display_lrc_preview)
preview_lrc_btn.pack(side=tk.LEFT, padx=10)

fix_lrc_btn = ttk.Button(karaoke_button_frame, text="Fix LRC Format", command=fix_lrc_file)
fix_lrc_btn.pack(side=tk.LEFT, padx=10)

# Make Force Create Video the main/default button - larger and more prominent
force_video_btn = ttk.Button(karaoke_button_frame, text="Create Karaoke Video", command=force_create_video, 
                          style="Accent.TButton")
force_video_btn.pack(side=tk.LEFT, padx=10)

# Rename the original button to "Legacy Create" and make it less prominent
create_video_btn = ttk.Button(karaoke_button_frame, text="Legacy Create", command=create_karaoke_video)
create_video_btn.pack(side=tk.LEFT, padx=10)

play_music_btn = ttk.Button(karaoke_button_frame, text="Play Music", command=play_music)
play_music_btn.pack(side=tk.LEFT, padx=10)

# Create a custom style for the accent button
style = ttk.Style()
style.configure("Accent.TButton", font=("Arial", 11, "bold"))

# Status and output area (shared between tabs)
status_label = ttk.Label(main_frame, text="Ready")
status_label.pack(pady=5, anchor=tk.W)

output_frame = ttk.Frame(main_frame)
output_frame.pack(fill=tk.BOTH, expand=True)

output_text = scrolledtext.ScrolledText(output_frame, width=80, height=20)
output_text.pack(fill=tk.BOTH, expand=True)

root.mainloop() 