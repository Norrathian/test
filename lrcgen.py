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
            
        # Try to fetch lyrics
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
    import subprocess
    import platform
    
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
        lyrics = [line.strip() for line in text.split('\n') if line.strip()]
    
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

# Set up GUI
root = tk.Tk()
root.title("LRC Creator")
root.geometry("700x550")

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
auto_tab = ttk.Frame(tab_control)
sync_tab = ttk.Frame(tab_control)

tab_control.add(auto_tab, text="Auto Generation")
tab_control.add(sync_tab, text="Manual Sync")

# === Auto Generation Tab ===
# Settings frame
settings_frame = ttk.LabelFrame(auto_tab, text="Settings")
settings_frame.pack(fill=tk.X, pady=5)

# Online lyrics checkbox
online_lyrics_check = ttk.Checkbutton(settings_frame, text="Search for lyrics online (recommended)", 
                                     variable=online_lyrics_var)
online_lyrics_check.grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)

# Interval setting (only used if not using online lyrics)
ttk.Label(settings_frame, text="Time interval if creating manual timestamps:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
interval_combo = ttk.Combobox(settings_frame, textvariable=interval_var, width=5)
interval_combo['values'] = ("1", "2", "3", "5", "10")
interval_combo.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)

# Create button frame
button_frame = ttk.Frame(auto_tab)
button_frame.pack(pady=5, fill=tk.X)

process_button = ttk.Button(button_frame, text="Create LRC File", command=process_file)
process_button.pack(side=tk.LEFT, padx=5)

load_button = ttk.Button(button_frame, text="Load LRC File", command=load_lyrics)
load_button.pack(side=tk.LEFT, padx=5)

save_button = ttk.Button(button_frame, text="Save LRC File", command=save_lyrics)
save_button.pack(side=tk.LEFT, padx=5)

play_button = ttk.Button(button_frame, text="Play Music", command=play_music)
play_button.pack(side=tk.LEFT, padx=5)

# Instructions
instruction_frame = ttk.Frame(auto_tab)
instruction_frame.pack(fill=tk.X, pady=5)
ttk.Label(instruction_frame, text="1. Make sure your MP3 filename is formatted as 'Artist - Title.mp3' for best results").pack(anchor=tk.W)
ttk.Label(instruction_frame, text="2. Click 'Create LRC File' to search for lyrics online and align them with the song").pack(anchor=tk.W)
ttk.Label(instruction_frame, text="3. Edit the lyrics and timing if needed").pack(anchor=tk.W)
ttk.Label(instruction_frame, text="4. Use 'Play Music' to check alignment while editing").pack(anchor=tk.W)
ttk.Label(instruction_frame, text="5. Save when finished").pack(anchor=tk.W)

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

# Status and output area (shared between tabs)
status_label = ttk.Label(main_frame, text="Ready")
status_label.pack(pady=5, anchor=tk.W)

output_frame = ttk.Frame(main_frame)
output_frame.pack(fill=tk.BOTH, expand=True)

output_text = scrolledtext.ScrolledText(output_frame, width=80, height=20)
output_text.pack(fill=tk.BOTH, expand=True)

root.mainloop()