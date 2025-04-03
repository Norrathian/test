import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from moviepy.editor import VideoFileClip, CompositeVideoClip, TextClip, vfx, AudioFileClip, concatenate_videoclips
from moviepy.config import change_settings
from PIL import Image, ImageTk
import numpy as np
from scipy.ndimage import binary_dilation
import threading
import json
import os
import time
import subprocess
import cv2  # Add OpenCV
import mediapipe as mp  # Add Mediapipe

print("Imports completed")

# Set ImageMagick path
change_settings({"IMAGEMAGICK_BINARY": r"C:\Program Files\ImageMagick-7.1.1-Q16-HDRI\magick.exe"})

# Custom resize function
def custom_resize(clip, width, height):
    try:
        def resize_frame(image):
            pil_image = Image.fromarray(image, mode='RGB')
            resized_image = pil_image.resize((width, height), Image.Resampling.LANCZOS)
            return np.array(resized_image)
        resized_clip = clip.fl_image(resize_frame)
        if resized_clip is None:
            raise ValueError("Resize returned None")
        print(f"Resized clip: {resized_clip.w}x{resized_clip.h}, duration={resized_clip.duration}")
        return resized_clip
    except Exception as e:
        print(f"Error in custom_resize: {str(e)}")
        return None

# Custom green keying function
def manual_key_green(image, bg_frame, green_lower, green_upper, dilation):
    img = np.array(image)
    bg = np.array(bg_frame)
    mask = np.all((img >= green_lower) & (img <= green_upper), axis=2)
    mask = binary_dilation(mask, iterations=dilation)
    img[mask] = bg[mask]
    return img

# Main processing function
def process_video(foreground_paths, background_path, output_base_path, text, text_color, text_size, text_pos, loop, fg_width, fg_height, bg_width, bg_height, audio_source, custom_audio_path, green_lower, green_upper, dilation, format, fps, transition, app):
    try:
        app.update_status(f"Starting {os.path.basename(output_base_path)}", "#d4a017")
        app.progress["value"] = 0
        total_files = len(foreground_paths)
        
        target_width = int(fg_width) if fg_width else (int(bg_width) if bg_width else None)
        target_height = int(fg_height) if fg_height else (int(bg_height) if bg_height else None)

        app.update_status("Loading background", "#d4a017")
        background = VideoFileClip(background_path)
        if background is None:
            raise ValueError(f"Failed to load background: {background_path}")
        print(f"Background loaded: {background.w}x{background.h}, duration={background.duration}")

        if not target_width or not target_height:
            app.update_status("Checking foreground for size", "#d4a017")
            first_fg = VideoFileClip(foreground_paths[0])
            if first_fg is None:
                raise ValueError(f"Failed to load first foreground: {foreground_paths[0]}")
            target_width, target_height = first_fg.w, first_fg.h
            first_fg.close()
            print(f"Set target size from foreground: {target_width}x{target_height}")

        if (background.w, background.h) != (target_width, target_height):
            app.update_status("Resizing background", "#d4a017")
            background = custom_resize(background, target_width, target_height)
            if background is None:
                raise ValueError("Background resize failed")
        print(f"Background ready: {background.w}x{background.h}, duration={background.duration}")

        clips = []
        for i, fg_path in enumerate(foreground_paths):
            app.update_status(f"Processing foreground {i+1}/{total_files}", "#d4a017")
            print(f"Processing file {i+1}/{total_files}: {fg_path}")
            foreground = VideoFileClip(fg_path)
            if foreground is None:
                raise ValueError(f"Failed to load foreground: {fg_path}")
            print(f"Foreground size (original): {foreground.w}x{foreground.h}, duration={foreground.duration}")

            duration = min(foreground.duration, background.duration)
            print(f"Calculated duration: {duration}")

            fg_sub = foreground
            bg_sub = background
            print(f"Using foreground: {fg_sub.w}x{fg_sub.h}, duration={fg_sub.duration}")
            print(f"Using background: {bg_sub.w}x{bg_sub.h}, duration={bg_sub.duration}")

            if (fg_sub.w, fg_sub.h) != (target_width, target_height):
                app.update_status(f"Resizing foreground {i+1}", "#d4a017")
                fg_sub = custom_resize(fg_sub, target_width, target_height)
                if fg_sub is None:
                    raise ValueError(f"Foreground resize failed for {fg_path}")

            app.update_status(f"Keying green screen {i+1}", "#d4a017")
            print("Applying green screen keying...")
            green_lower_array = np.array([int(green_lower[0]), int(green_lower[1]), int(green_lower[2])])
            green_upper_array = np.array([int(green_upper[0]), int(green_upper[1]), int(green_upper[2])])
            foreground_keyed = fg_sub.fl(lambda gf, t: manual_key_green(gf(t), bg_sub.get_frame(t % bg_sub.duration), green_lower_array, green_upper_array, dilation))

            layers = [bg_sub, foreground_keyed]
            if text.strip():
                app.update_status(f"Adding text to {i+1}", "#d4a017")
                print("Adding text overlay...")
                pos_map = {
                    "Top Left": ("left", 50),
                    "Top Center": ("center", 50),
                    "Top Right": ("right", 50),
                    "Center": ("center", "center"),
                    "Bottom Left": ("left", target_height - 50),
                    "Bottom Center": ("center", target_height - 50),
                    "Bottom Right": ("right", target_height - 50)
                }
                hud = TextClip(text, fontsize=text_size, color=text_color, font="Arial").set_position(pos_map[text_pos]).set_duration(duration)
                layers.append(hud)

            app.update_status(f"Compositing {i+1}", "#d4a017")
            print("Compositing layers...")
            clip = CompositeVideoClip(layers, size=(target_width, target_height))
            if clip is None:
                raise ValueError(f"CompositeVideoClip failed for {fg_path}")
            clips.append(clip)

            app.progress["value"] = ((i + 1) / total_files) * 100
            app.root.update_idletasks()

        app.update_status("Combining clips", "#d4a017")
        print("Combining clips...")
        if len(clips) > 1 and transition:
            final_video = concatenate_videoclips(clips, method="compose", transition=vfx.fadeout(0.5).set_duration(0.5))
        else:
            final_video = clips[0] if len(clips) == 1 else concatenate_videoclips(clips, method="compose")
        if final_video is None:
            raise ValueError("Clip combination failed")

        final_duration = min([VideoFileClip(fg).duration for fg in foreground_paths])
        app.update_status("Trimming duration", "#d4a017")
        final_video = final_video.set_duration(final_duration)
        print(f"Final video duration trimmed to: {final_video.duration}")
        if final_video is None:
            raise ValueError("Set duration failed")

        if audio_source == "Foreground":
            app.update_status("Adding foreground audio", "#d4a017")
            print("Setting foreground audio...")
            audio_clip = VideoFileClip(foreground_paths[0])
            if audio_clip.audio is None:
                print("No audio in foreground—skipping audio.")
            else:
                audio = audio_clip.audio.set_duration(final_video.duration)
                if audio is not None:
                    final_video = final_video.set_audio(audio)
                else:
                    print("Audio setting failed—proceeding without audio.")
            audio_clip.close()
        elif audio_source == "Background":
            app.update_status("Adding background audio", "#d4a017")
            print("Setting background audio...")
            audio_clip = VideoFileClip(background_path)
            if audio_clip.audio is None:
                print("No audio in background—skipping audio.")
            else:
                audio = audio_clip.audio.set_duration(final_video.duration)
                if audio is not None:
                    final_video = final_video.set_audio(audio)
                else:
                    print("Audio setting failed—proceeding without audio.")
            audio_clip.close()
        elif audio_source == "Custom" and custom_audio_path:
            app.update_status("Adding custom audio", "#d4a017")
            print("Setting custom audio...")
            custom_audio = AudioFileClip(custom_audio_path)
            if custom_audio is None:
                print("Failed to load custom audio—skipping.")
            else:
                audio = custom_audio.set_duration(final_video.duration)
                if audio is not None:
                    final_video = final_video.set_audio(audio)
                else:
                    print("Audio setting failed—proceeding without audio.")

        if final_video is None:
            raise ValueError("Final video is None before writing")

        output_path = output_base_path
        codec_map = {"MP4": "libx264", "AVI": "mpeg4", "MOV": "libx264"}
        app.update_status(f"Writing {os.path.basename(output_path)}", "#d4a017")
        print(f"Writing video: {output_path}")
        ffmpeg_params = ["-loop", "0"] if loop else []
        print(f"FFmpeg params: {ffmpeg_params}")
        final_video.write_videofile(output_path, fps=int(fps), codec=codec_map[format], logger=None, ffmpeg_params=ffmpeg_params)
        print("Video processing complete:", output_path)

        app.last_output = output_path
        print(f"Set app.last_output to: {app.last_output}")
        app.add_recent_file(output_path)
        app.update_status(f"Done: {os.path.basename(output_path)}", "#27ae60")
        messagebox.showinfo("Success", f"Processed {total_files} video(s)!")
        if app.export_log.get():
            with open(os.path.join(os.path.dirname(output_path), "process_log.txt"), "a") as f:
                f.write(f"{time.ctime()}: Processed {output_path} ({final_duration}s, {target_width}x{target_height})\n")
    except Exception as e:
        print(f"Error: {str(e)}")
        app.update_status(f"Error: {str(e)[:50]}", "#c0392b")
        messagebox.showerror("Error", f"Processing failed: {str(e)}")
    finally:
        print(f"Calling enable_button, last_output: {app.last_output}, exists: {os.path.exists(app.last_output) if app.last_output else False}")
        app.root.after(0, app.enable_button)

# Preview function
def preview_frame(foreground_path, background_path, fg_width, fg_height, bg_width, bg_height, green_lower, green_upper, dilation):
    foreground = VideoFileClip(foreground_path)
    if foreground is None:
        raise ValueError(f"Failed to load preview foreground: {foreground_path}")
    background = VideoFileClip(background_path)
    if background is None:
        raise ValueError(f"Failed to load preview background: {background_path}")

    duration = min(foreground.duration, background.duration)
    target_width = int(fg_width) if fg_width else (int(bg_width) if bg_width else foreground.w)
    target_height = int(fg_height) if fg_height else (int(bg_height) if bg_height else foreground.h)

    if (foreground.w, foreground.h) != (target_width, target_height):
        foreground = custom_resize(foreground, target_width, target_height)
    if (background.w, background.h) != (target_width, target_height):
        background = custom_resize(background, target_width, target_height)

    frame = manual_key_green(foreground.get_frame(1 % foreground.duration), background.get_frame(1 % background.duration), np.array(green_lower), np.array(green_upper), dilation)
    return Image.fromarray(frame)

# Tooltip class
class Tooltip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        self.widget.bind("<Enter>", self.show_tip)
        self.widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event):
        if self.tip_window or not self.text:
            return
        x, y = self.widget.winfo_rootx() + 25, self.widget.winfo_rooty() + 25
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = ttk.Label(tw, text=self.text, background="#2c3e50", foreground="#ecf0f1", relief="solid", borderwidth=1, padding=4, font=("Helvetica", 9))
        label.pack()

    def hide_tip(self, event):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None

# GUI class
class VideoProcessorApp:
    def __init__(self, root):
        print("Starting VideoProcessorApp.__init__")
        self.root = root
        self.root.title("Green Screen Video Editor v1.3")
        self.root.geometry("650x850")
        self.root.configure(bg="#f5f6f5")
        self.theme = "Light"
        self.last_output = None

        # Style configuration
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TButton", font=("Helvetica", 10, "bold"), padding=6, background="#2ecc71", foreground="#ffffff", borderwidth=0, relief="flat")
        style.map("TButton", background=[("active", "#27ae60"), ("disabled", "#95a5a6")], foreground=[("disabled", "#d5d8dc")])
        style.configure("TLabel", font=("Helvetica", 10), background="#f5f6f5", foreground="#2c3e50")
        style.configure("TFrame", background="#f5f6f5")
        style.configure("TCheckbutton", font=("Helvetica", 10), background="#f5f6f5", foreground="#2c3e50")
        style.configure("TScale", background="#f5f6f5", troughcolor="#dfe4ea")
        style.configure("TProgressbar", background="#2ecc71", troughcolor="#dfe4ea")
        style.configure("TNotebook", background="#f5f6f5", tabposition="nw")
        style.configure("TNotebook.Tab", font=("Helvetica", 10, "bold"), padding=[10, 5], background="#dfe4ea")
        style.map("TNotebook.Tab", background=[("selected", "#ffffff")])

        # Main frame with scrollbar
        self.canvas = tk.Canvas(self.root, bg="#f5f6f5", highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=self.canvas.yview)
        self.main_frame = ttk.Frame(self.canvas)

        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True, padx=20, pady=20)
        self.canvas.create_window((0, 0), window=self.main_frame, anchor="nw")
        self.main_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        # Variables
        self.foreground_paths = []
        self.background_path = tk.StringVar()
        self.output_path = tk.StringVar(value="C:/Users/Haley/Desktop/green/output.mp4")
        self.fg_size = tk.StringVar(value="Not selected")
        self.bg_size = tk.StringVar(value="Not selected")
        self.status = tk.StringVar(value="Ready")
        self.status_color = tk.StringVar(value="#2c3e50")
        self.text_input = tk.StringVar()
        self.text_color = tk.StringVar(value="white")
        self.text_size = tk.IntVar(value=24)
        self.text_pos = tk.StringVar(value="Top Left")
        self.loop_video = tk.BooleanVar(value=False)
        self.fg_width = tk.StringVar()
        self.fg_height = tk.StringVar()
        self.bg_width = tk.StringVar()
        self.bg_height = tk.StringVar()
        self.fg_preset = tk.StringVar(value="Native")
        self.bg_preset = tk.StringVar(value="Native")
        self.audio_source = tk.StringVar(value="Foreground")
        self.custom_audio_path = tk.StringVar()
        self.green_lower_r = tk.IntVar(value=0)
        self.green_lower_g = tk.IntVar(value=120)
        self.green_lower_b = tk.IntVar(value=0)
        self.green_upper_r = tk.IntVar(value=120)
        self.green_upper_g = tk.IntVar(value=255)
        self.green_upper_b = tk.IntVar(value=120)
        self.dilation = tk.IntVar(value=1)
        self.format = tk.StringVar(value="MP4")
        self.fps = tk.StringVar(value="24")
        self.transition = tk.BooleanVar(value=False)
        self.export_log = tk.BooleanVar(value=False)
        self.recent_files = []

        self.size_presets = {
            "Native": (None, None),
            "Instagram (1080x1080)": (1080, 1080),
            "YouTube (1920x1080)": (1920, 1080),
            "TikTok (1080x1920)": (1080, 1920),
            "Custom": (None, None)
        }

        # Header
        header_frame = ttk.Frame(self.main_frame, relief="flat")
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        ttk.Label(header_frame, text="Green Screen Video Editor", font=("Helvetica", 18, "bold")).pack(side="left")
        ttk.Label(header_frame, text="v1.3", font=("Helvetica", 8)).pack(side="left", padx=5)
        theme_menu = ttk.OptionMenu(header_frame, tk.StringVar(value="Light"), "Light", "Dark", "Slate", command=self.set_theme)
        theme_menu.pack(side="right")
        Tooltip(theme_menu, "Switch UI theme")

        # Inputs
        input_frame = ttk.LabelFrame(self.main_frame, text="Inputs", padding=10)
        input_frame.grid(row=1, column=0, sticky="ew", pady=5)
        input_frame.configure(relief="flat", borderwidth=0)

        ttk.Label(input_frame, text="Foreground Video(s):").grid(row=0, column=0, sticky="w")
        fg_btn_frame = ttk.Frame(input_frame)
        fg_btn_frame.grid(row=0, column=1, sticky="e")
        ttk.Button(fg_btn_frame, text="Add", command=self.add_foreground, style="TButton").pack(side="left", padx=5)
        ttk.Button(fg_btn_frame, text="Clear", command=self.clear_foregrounds, style="TButton").pack(side="left", padx=5)
        self.fg_listbox = tk.Listbox(input_frame, height=4, font=("Helvetica", 9), bg="#ffffff", relief="flat", borderwidth=1, selectbackground="#dfe4ea")
        self.fg_listbox.grid(row=1, column=0, columnspan=2, sticky="ew", pady=5)
        ttk.Label(input_frame, textvariable=self.fg_size, font=("Helvetica", 9)).grid(row=2, column=0, columnspan=2, sticky="w")

        ttk.Label(input_frame, text="Background Video:").grid(row=3, column=0, sticky="w")
        ttk.Button(input_frame, text="Browse", command=self.select_background, style="TButton").grid(row=3, column=1, sticky="e", padx=5)
        ttk.Label(input_frame, textvariable=self.background_path, wraplength=400, font=("Helvetica", 9)).grid(row=4, column=0, columnspan=2, sticky="w")
        ttk.Label(input_frame, textvariable=self.bg_size, font=("Helvetica", 9)).grid(row=5, column=0, columnspan=2, sticky="w")

        ttk.Label(input_frame, text="Output Path:").grid(row=6, column=0, sticky="w")
        ttk.Button(input_frame, text="Browse", command=self.select_output, style="TButton").grid(row=6, column=1, sticky="e", padx=5)
        ttk.Label(input_frame, textvariable=self.output_path, wraplength=400, font=("Helvetica", 9)).grid(row=7, column=0, columnspan=2, sticky="w")

        # Tabbed Settings
        settings_notebook = ttk.Notebook(self.main_frame)
        settings_notebook.grid(row=2, column=0, sticky="ew", pady=10)

        # Basic Tab
        basic_tab = ttk.Frame(settings_notebook, padding=10)
        settings_notebook.add(basic_tab, text="Basic")

        ttk.Label(basic_tab, text="Foreground Size:").grid(row=0, column=0, sticky="w")
        ttk.OptionMenu(basic_tab, self.fg_preset, *self.size_presets.keys(), command=lambda v: self.set_preset_size(v, "fg")).grid(row=0, column=1, sticky="ew", padx=5)
        fg_size_frame = ttk.Frame(basic_tab)
        fg_size_frame.grid(row=1, column=0, columnspan=2, pady=2)
        ttk.Entry(fg_size_frame, textvariable=self.fg_width, width=8, justify="center", background="#ffffff").pack(side="left", padx=2)
        ttk.Label(fg_size_frame, text="x").pack(side="left")
        ttk.Entry(fg_size_frame, textvariable=self.fg_height, width=8, justify="center", background="#ffffff").pack(side="left", padx=2)

        ttk.Label(basic_tab, text="Background Size:").grid(row=2, column=0, sticky="w")
        ttk.OptionMenu(basic_tab, self.bg_preset, *self.size_presets.keys(), command=lambda v: self.set_preset_size(v, "bg")).grid(row=2, column=1, sticky="ew", padx=5)
        bg_size_frame = ttk.Frame(basic_tab)
        bg_size_frame.grid(row=3, column=0, columnspan=2, pady=2)
        ttk.Entry(bg_size_frame, textvariable=self.bg_width, width=8, justify="center", background="#ffffff").pack(side="left", padx=2)
        ttk.Label(bg_size_frame, text="x").pack(side="left")
        ttk.Entry(bg_size_frame, textvariable=self.bg_height, width=8, justify="center", background="#ffffff").pack(side="left", padx=2)

        ttk.Label(basic_tab, text="Overlay Text:").grid(row=4, column=0, sticky="w")
        ttk.Entry(basic_tab, textvariable=self.text_input, background="#ffffff").grid(row=4, column=1, sticky="ew", pady=5, padx=5)

        # Advanced Tab
        advanced_tab = ttk.Frame(settings_notebook, padding=10)
        settings_notebook.add(advanced_tab, text="Advanced")

        ttk.Label(advanced_tab, text="Text Color:").grid(row=0, column=0, sticky="w")
        ttk.OptionMenu(advanced_tab, self.text_color, "white", "black", "red", "blue", "yellow").grid(row=0, column=1, sticky="ew", padx=5)
        ttk.Label(advanced_tab, text="Text Size:").grid(row=1, column=0, sticky="w")
        ttk.Scale(advanced_tab, from_=10, to=100, orient="horizontal", variable=self.text_size).grid(row=1, column=1, sticky="ew", padx=5)
        ttk.Label(advanced_tab, text="Text Position:").grid(row=2, column=0, sticky="w")
        ttk.OptionMenu(advanced_tab, self.text_pos, "Top Left", "Top Center", "Top Right", "Center", "Bottom Left", "Bottom Center", "Bottom Right").grid(row=2, column=1, sticky="ew", padx=5)

        ttk.Label(advanced_tab, text="Audio Source:").grid(row=3, column=0, sticky="w")
        ttk.OptionMenu(advanced_tab, self.audio_source, "Foreground", "Background", "Custom", command=self.toggle_audio_entry).grid(row=3, column=1, sticky="ew", padx=5)
        self.audio_frame = ttk.Frame(advanced_tab)
        self.audio_frame.grid(row=4, column=0, columnspan=2, sticky="ew", pady=5)
        ttk.Button(self.audio_frame, text="Browse", command=self.select_audio, style="TButton").pack(side="left", padx=5)
        ttk.Label(self.audio_frame, textvariable=self.custom_audio_path, wraplength=300, font=("Helvetica", 9)).pack(side="left")
        self.audio_frame.grid_remove()

        ttk.Label(advanced_tab, text="Green Lower RGB:").grid(row=5, column=0, sticky="w")
        lower_frame = ttk.Frame(advanced_tab)
        lower_frame.grid(row=5, column=1, sticky="ew")
        ttk.Entry(lower_frame, textvariable=self.green_lower_r, width=5, justify="center", background="#ffffff").pack(side="left", padx=2)
        ttk.Entry(lower_frame, textvariable=self.green_lower_g, width=5, justify="center", background="#ffffff").pack(side="left", padx=2)
        ttk.Entry(lower_frame, textvariable=self.green_lower_b, width=5, justify="center", background="#ffffff").pack(side="left", padx=2)

        ttk.Label(advanced_tab, text="Green Upper RGB:").grid(row=6, column=0, sticky="w")
        upper_frame = ttk.Frame(advanced_tab)
        upper_frame.grid(row=6, column=1, sticky="ew")
        ttk.Entry(upper_frame, textvariable=self.green_upper_r, width=5, justify="center", background="#ffffff").pack(side="left", padx=2)
        ttk.Entry(upper_frame, textvariable=self.green_upper_g, width=5, justify="center", background="#ffffff").pack(side="left", padx=2)
        ttk.Entry(upper_frame, textvariable=self.green_upper_b, width=5, justify="center", background="#ffffff").pack(side="left", padx=2)

        ttk.Label(advanced_tab, text="Dilation:").grid(row=7, column=0, sticky="w")
        ttk.Scale(advanced_tab, from_=0, to=5, orient="horizontal", variable=self.dilation).grid(row=7, column=1, sticky="ew", padx=5)

        # Output Tab
        output_tab = ttk.Frame(settings_notebook, padding=10)
        settings_notebook.add(output_tab, text="Output")

        ttk.Label(output_tab, text="Format:").grid(row=0, column=0, sticky="w")
        ttk.OptionMenu(output_tab, self.format, "MP4", "AVI", "MOV").grid(row=0, column=1, sticky="ew", padx=5)
        ttk.Label(output_tab, text="FPS:").grid(row=1, column=0, sticky="w")
        ttk.Entry(output_tab, textvariable=self.fps, width=5, justify="center", background="#ffffff").grid(row=1, column=1, sticky="w", padx=5, pady=5)
        ttk.Checkbutton(output_tab, text="Loop Video", variable=self.loop_video).grid(row=2, column=0, sticky="w")
        ttk.Checkbutton(output_tab, text="Fade Transition", variable=self.transition).grid(row=2, column=1, sticky="w")
        ttk.Checkbutton(output_tab, text="Export Log", variable=self.export_log).grid(row=3, column=0, sticky="w")

        # Recent Files
        recent_frame = ttk.LabelFrame(self.main_frame, text="Recent Outputs", padding=10)
        recent_frame.grid(row=3, column=0, sticky="ew", pady=5)
        recent_frame.configure(relief="flat", borderwidth=0)
        self.recent_listbox = tk.Listbox(recent_frame, height=3, font=("Helvetica", 9), bg="#ffffff", relief="flat", borderwidth=1, selectbackground="#dfe4ea")
        self.recent_listbox.grid(row=0, column=0, sticky="ew")
        self.recent_listbox.bind("<Double-1>", self.load_recent_file)

        # Controls
        control_frame = ttk.Frame(self.main_frame)
        control_frame.grid(row=4, column=0, sticky="ew", pady=15)
        self.preview_btn = ttk.Button(control_frame, text="Preview", command=self.show_preview, style="TButton")
        self.preview_btn.grid(row=0, column=0, padx=5)
        Tooltip(self.preview_btn, "Preview a single frame (Ctrl+P)")
        ttk.Button(control_frame, text="Save Preset", command=self.save_preset, style="TButton").grid(row=0, column=1, padx=5)
        ttk.Button(control_frame, text="Load Preset", command=self.load_preset, style="TButton").grid(row=0, column=2, padx=5)
        self.reset_btn = ttk.Button(control_frame, text="Reset", command=self.reset_settings, style="TButton")
        self.reset_btn.grid(row=0, column=3, padx=5)
        Tooltip(self.reset_btn, "Reset all settings (Ctrl+R)")
        self.run_button = ttk.Button(control_frame, text="Process", command=self.run_processing, style="TButton")
        self.run_button.grid(row=0, column=4, padx=5)
        Tooltip(self.run_button, "Start processing (Ctrl+Enter)")
        self.open_button = ttk.Button(control_frame, text="Open Output", command=self.open_output, style="TButton", state="disabled")
        self.open_button.grid(row=0, column=5, padx=5)
        Tooltip(self.open_button, "Open last processed video")
        self.convert_btn = ttk.Button(control_frame, text="Convert to Green", command=self.convert_to_green, style="TButton")
        self.convert_btn.grid(row=0, column=6, padx=5)
        Tooltip(self.convert_btn, "Convert video to green screen foreground")

        # Status Bar
        status_frame = ttk.Frame(self.main_frame, relief="flat", borderwidth=0)
        status_frame.grid(row=5, column=0, sticky="ew", pady=5)
        ttk.Label(status_frame, text="Progress:").grid(row=0, column=0, sticky="w", padx=5)
        self.progress = ttk.Progressbar(status_frame, maximum=100, length=500, mode="determinate")
        self.progress.grid(row=0, column=1, sticky="ew", padx=5, pady=2)
        ttk.Label(status_frame, text="Status:").grid(row=1, column=0, sticky="w", padx=5)
        self.status_label = ttk.Label(status_frame, textvariable=self.status, foreground=self.status_color.get(), font=("Helvetica", 10, "bold"))
        self.status_label.grid(row=1, column=1, sticky="w", padx=5, pady=2)

        # Configure grid weights
        self.main_frame.columnconfigure(0, weight=1)
        input_frame.columnconfigure(0, weight=1)
        basic_tab.columnconfigure(1, weight=1)
        advanced_tab.columnconfigure(1, weight=1)
        output_tab.columnconfigure(1, weight=1)
        recent_frame.columnconfigure(0, weight=1)
        control_frame.columnconfigure(6, weight=1)  # Updated to 6 for new button
        status_frame.columnconfigure(1, weight=1)

        # Keyboard shortcuts
        self.root.bind("<Control-p>", lambda e: self.show_preview())
        self.root.bind("<Control-r>", lambda e: self.reset_settings())
        self.root.bind("<Control-Return>", lambda e: self.run_processing())

        print("VideoProcessorApp.__init__ completed")

    def add_foreground(self):
        path = filedialog.askopenfilename(filetypes=[("Video files", "*.mp4")])
        if path:
            self.foreground_paths.append(path)
            self.fg_listbox.insert(tk.END, os.path.basename(path))
            try:
                clip = VideoFileClip(path)
                self.fg_size.set(f"Last added: {clip.w}x{clip.h}, {clip.duration:.2f}s")
                clip.close()
            except Exception as e:
                self.fg_size.set(f"Error: {str(e)}")

    def clear_foregrounds(self):
        self.foreground_paths.clear()
        self.fg_listbox.delete(0, tk.END)
        self.fg_size.set("Not selected")

    def select_background(self):
        path = filedialog.askopenfilename(filetypes=[("Video files", "*.mp4")])
        if path:
            self.background_path.set(path)
            try:
                clip = VideoFileClip(path)
                self.bg_size.set(f"Size: {clip.w}x{clip.h}, {clip.duration:.2f}s")
                clip.close()
            except Exception as e:
                self.bg_size.set(f"Error: {str(e)}")

    def select_output(self):
        path = filedialog.asksaveasfilename(defaultextension=f".{self.format.get().lower()}", filetypes=[("Video files", f"*.{self.format.get().lower()}")])
        if path:
            self.output_path.set(path)

    def select_audio(self):
        path = filedialog.askopenfilename(filetypes=[("Audio files", "*.mp3 *.wav")])
        if path:
            self.custom_audio_path.set(path)

    def set_preset_size(self, preset, target):
        width, height = self.size_presets[preset]
        if target == "fg":
            if width and height:
                self.fg_width.set(str(width))
                self.fg_height.set(str(height))
            else:
                self.fg_width.set("")
                self.fg_height.set("")
        elif target == "bg":
            if width and height:
                self.bg_width.set(str(width))
                self.bg_height.set(str(height))
            else:
                self.bg_width.set("")
                self.bg_height.set("")

    def toggle_audio_entry(self, *args):
        if self.audio_source.get() == "Custom":
            self.audio_frame.grid()
        else:
            self.audio_frame.grid_remove()

    def set_theme(self, theme):
        self.theme = theme
        if theme == "Light":
            bg, fg, btn, btn_active, trough = "#f5f6f5", "#2c3e50", "#2ecc71", "#27ae60", "#dfe4ea"
        elif theme == "Dark":
            bg, fg, btn, btn_active, trough = "#2c3e50", "#ecf0f1", "#3498db", "#2980b9", "#34495e"
        elif theme == "Slate":
            bg, fg, btn, btn_active, trough = "#576574", "#dfe4ea", "#e67e22", "#d35400", "#718093"
        
        self.root.configure(bg=bg)
        self.canvas.configure(bg=bg)
        self.fg_listbox.configure(bg="#ffffff" if theme == "Light" else trough, fg=fg)
        self.recent_listbox.configure(bg="#ffffff" if theme == "Light" else trough, fg=fg)
        style = ttk.Style()
        style.configure("TLabel", background=bg, foreground=fg)
        style.configure("TFrame", background=bg)
        style.configure("TCheckbutton", background=bg, foreground=fg)
        style.configure("TScale", background=bg, troughcolor=trough)
        style.configure("TButton", background=btn, foreground="#ffffff")
        style.map("TButton", background=[("active", btn_active), ("disabled", "#95a5a6")], foreground=[("disabled", "#d5d8dc")])
        style.configure("TProgressbar", background=btn, troughcolor=trough)
        style.configure("TNotebook", background=bg)
        style.configure("TNotebook.Tab", background=trough if theme != "Light" else "#dfe4ea")
        style.map("TNotebook.Tab", background=[("selected", "#ffffff" if theme == "Light" else trough)])
        self.status_label.configure(foreground=self.status_color.get())
        for widget in self.main_frame.winfo_children():
            for child in widget.winfo_children():
                if isinstance(child, ttk.Entry):
                    child.configure(background="#ffffff" if theme == "Light" else trough)
        for btn in [self.preview_btn, self.reset_btn, self.run_button, self.open_button, self.convert_btn]:  # Added convert_btn
            btn.configure(style="TButton")

    def reset_settings(self):
        self.text_input.set("")
        self.text_color.set("white")
        self.text_size.set(24)
        self.text_pos.set("Top Left")
        self.loop_video.set(False)
        self.fg_width.set("")
        self.fg_height.set("")
        self.bg_width.set("")
        self.bg_height.set("")
        self.fg_preset.set("Native")
        self.bg_preset.set("Native")
        self.audio_source.set("Foreground")
        self.custom_audio_path.set("")
        self.green_lower_r.set(0)
        self.green_lower_g.set(120)
        self.green_lower_b.set(0)
        self.green_upper_r.set(120)
        self.green_upper_g.set(255)
        self.green_upper_b.set(120)
        self.dilation.set(1)
        self.format.set("MP4")
        self.fps.set("24")
        self.transition.set(False)
        self.export_log.set(False)
        self.toggle_audio_entry()

    def show_preview(self):
        if not self.foreground_paths or not self.background_path.get():
            messagebox.showwarning("Input Error", "Select foreground and background first!")
            return
        try:
            green_lower = (self.green_lower_r.get(), self.green_lower_g.get(), self.green_lower_b.get())
            green_upper = (self.green_upper_r.get(), self.green_upper_g.get(), self.green_upper_b.get())
            preview_img = preview_frame(self.foreground_paths[0], self.background_path.get(), self.fg_width.get(), self.fg_height.get(), self.bg_width.get(), self.bg_height.get(), green_lower, green_upper, self.dilation.get())
            preview_img = preview_img.resize((300, int(300 * preview_img.height / preview_img.width)), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(preview_img)
            preview_window = tk.Toplevel(self.root)
            preview_window.title("Preview")
            preview_window.configure(bg="#2c3e50" if self.theme != "Light" else "#f5f6f5")
            ttk.Label(preview_window, image=photo).pack(padx=10, pady=10)
            preview_window.photo = photo
        except Exception as e:
            messagebox.showerror("Preview Error", str(e))

    def save_preset(self):
        settings = {
            "fg_width": self.fg_width.get(),
            "fg_height": self.fg_height.get(),
            "bg_width": self.bg_width.get(),
            "bg_height": self.bg_height.get(),
            "text": self.text_input.get(),
            "text_color": self.text_color.get(),
            "text_size": self.text_size.get(),
            "text_pos": self.text_pos.get(),
            "loop": self.loop_video.get(),
            "audio_source": self.audio_source.get(),
            "custom_audio_path": self.custom_audio_path.get(),
            "green_lower": (self.green_lower_r.get(), self.green_lower_g.get(), self.green_lower_b.get()),
            "green_upper": (self.green_upper_r.get(), self.green_upper_g.get(), self.green_upper_b.get()),
            "dilation": self.dilation.get(),
            "format": self.format.get(),
            "fps": self.fps.get(),
            "transition": self.transition.get(),
            "export_log": self.export_log.get()
        }
        main_dir = os.path.dirname(os.path.abspath(__file__))
        presets_dir = os.path.join(main_dir, "presets")
        
        os.makedirs(presets_dir, exist_ok=True)
        
        existing_files = [f for f in os.listdir(presets_dir) if f.startswith("preset") and f.endswith(".json")]
        if existing_files:
            numbers = [int(f.replace("preset", "").replace(".json", "")) for f in existing_files if f.replace("preset", "").replace(".json", "").isdigit()]
            next_num = max(numbers) + 1 if numbers else 1
        else:
            next_num = 1
        default_name = f"preset{next_num}.json"
        
        path = filedialog.asksaveasfilename(
            initialdir=presets_dir,
            initialfile=default_name,
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")]
        )
        if path:
            with open(path, 'w') as f:
                json.dump(settings, f)
            messagebox.showinfo("Success", f"Preset saved to {path}!")

    def load_preset(self):
        main_dir = os.path.dirname(os.path.abspath(__file__))
        presets_dir = os.path.join(main_dir, "presets")
        
        path = filedialog.askopenfilename(
            initialdir=presets_dir,
            filetypes=[("JSON files", "*.json")]
        )
        if path:
            with open(path, 'r') as f:
                settings = json.load(f)
            self.fg_width.set(settings.get("fg_width", ""))
            self.fg_height.set(settings.get("fg_height", ""))
            self.bg_width.set(settings.get("bg_width", ""))
            self.bg_height.set(settings.get("bg_height", ""))
            self.text_input.set(settings.get("text", ""))
            self.text_color.set(settings.get("text_color", "white"))
            self.text_size.set(settings.get("text_size", 24))
            self.text_pos.set(settings.get("text_pos", "Top Left"))
            self.loop_video.set(settings.get("loop", False))
            self.audio_source.set(settings.get("audio_source", "Foreground"))
            self.custom_audio_path.set(settings.get("custom_audio_path", ""))
            self.green_lower_r.set(settings["green_lower"][0])
            self.green_lower_g.set(settings["green_lower"][1])
            self.green_lower_b.set(settings["green_lower"][2])
            self.green_upper_r.set(settings["green_upper"][0])
            self.green_upper_g.set(settings["green_upper"][1])
            self.green_upper_b.set(settings["green_upper"][2])
            self.dilation.set(settings.get("dilation", 1))
            self.format.set(settings.get("format", "MP4"))
            self.fps.set(settings.get("fps", "24"))
            self.transition.set(settings.get("transition", False))
            self.export_log.set(settings.get("export_log", False))
            self.toggle_audio_entry()
            messagebox.showinfo("Success", "Preset loaded!")

    def add_recent_file(self, path):
        if path not in self.recent_files:
            self.recent_files.insert(0, path)
            self.recent_listbox.insert(0, os.path.basename(path))
            if len(self.recent_files) > 5:
                self.recent_files.pop()
                self.recent_listbox.delete(tk.END)

    def load_recent_file(self, event):
        selection = self.recent_listbox.curselection()
        if selection:
            path = self.recent_files[selection[0]]
            self.output_path.set(path)
            messagebox.showinfo("Recent File", f"Selected recent output: {path}")

    def run_processing(self):
        if not self.foreground_paths or not self.background_path.get() or not self.output_path.get():
            messagebox.showwarning("Input Error", "Please select all required files!")
            return
        try:
            fps = int(self.fps.get())
            if fps <= 0:
                raise ValueError("FPS must be positive")
        except ValueError:
            messagebox.showwarning("Input Error", "Invalid FPS value!")
            return
        self.run_button.config(state="disabled")
        self.open_button.config(state="disabled")
        self.convert_btn.config(state="disabled")  # Disable during processing
        for _ in range(3):
            self.progress["value"] = 50
            self.root.update_idletasks()
            time.sleep(0.1)
            self.progress["value"] = 0
            self.root.update_idletasks()
            time.sleep(0.1)
        green_lower = (self.green_lower_r.get(), self.green_lower_g.get(), self.green_lower_b.get())
        green_upper = (self.green_upper_r.get(), self.green_upper_g.get(), self.green_upper_b.get())
        thread = threading.Thread(target=process_video, args=(self.foreground_paths, self.background_path.get(), self.output_path.get(), self.text_input.get(), self.text_color.get(), self.text_size.get(), self.text_pos.get(), self.loop_video.get(), self.fg_width.get(), self.fg_height.get(), self.bg_width.get(), self.bg_height.get(), self.audio_source.get(), self.custom_audio_path.get(), green_lower, green_upper, self.dilation.get(), self.format.get(), self.fps.get(), self.transition.get(), self))
        thread.start()

    def open_output(self):
        if self.last_output and os.path.exists(self.last_output):
            try:
                subprocess.Popen(['start', self.last_output], shell=True)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to open file: {str(e)}")
        else:
            messagebox.showwarning("No Output", "No processed video available to open!")

    def convert_to_green(self):
        path = filedialog.askopenfilename(filetypes=[("Video files", "*.mp4")])
        if not path:
            return
        
        self.convert_btn.config(state="disabled")
        self.run_button.config(state="disabled")
        
        def process_conversion():
            try:
                mp_selfie_segmentation = mp.solutions.selfie_segmentation
                segmentation = mp_selfie_segmentation.SelfieSegmentation(model_selection=1)
                
                cap = cv2.VideoCapture(path)
                if not cap.isOpened():
                    raise ValueError("Could not open input video")
                
                fps = int(cap.get(cv2.CAP_PROP_FPS))
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                
                main_dir = os.path.dirname(os.path.abspath(__file__))
                output_path = os.path.join(main_dir, "foregrounds", f"greenscreen_{os.path.basename(path)}")
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                out = cv2.VideoWriter(output_path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
                
                self.update_status("Converting to green screen...", "#d4a017")
                frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                processed_frames = 0
                
                while cap.isOpened():
                    ret, frame = cap.read()
                    if not ret:
                        break
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    results = segmentation.process(rgb_frame)
                    mask = results.segmentation_mask > 0.5
                    green_bg = np.zeros_like(frame, dtype=np.uint8)
                    green_bg[:] = [0, 255, 0]  # Green in BGR
                    result = np.where(mask[..., None], frame, green_bg)
                    out.write(result)
                    
                    processed_frames += 1
                    self.progress["value"] = (processed_frames / frame_count) * 100
                    self.root.update_idletasks()
                
                cap.release()
                out.release()
                self.update_status("Conversion complete!", "#27ae60")
                self.foreground_paths.append(output_path)
                self.fg_listbox.insert(tk.END, os.path.basename(output_path))
                try:
                    clip = VideoFileClip(output_path)
                    self.fg_size.set(f"Last added: {clip.w}x{clip.h}, {clip.duration:.2f}s")
                    clip.close()
                except Exception as e:
                    self.fg_size.set(f"Error: {str(e)}")
                messagebox.showinfo("Success", f"Green screen video saved as {output_path} and added to foregrounds!")
            except Exception as e:
                print(f"Conversion error: {str(e)}")
                self.update_status(f"Error: {str(e)[:50]}", "#c0392b")
                messagebox.showerror("Error", f"Conversion failed: {str(e)}")
            finally:
                self.root.after(0, lambda: self.convert_btn.config(state="normal"))
                self.root.after(0, lambda: self.run_button.config(state="normal"))
        
        thread = threading.Thread(target=process_conversion)
        thread.start()

    def update_status(self, text, color="#2c3e50"):
        self.status.set(text)
        self.status_color.set(color)
        self.status_label.configure(foreground=color)
        self.root.update_idletasks()

    def enable_button(self):
        self.run_button.config(state="normal")
        self.convert_btn.config(state="normal")  # Re-enable convert button
        print(f"enable_button: last_output = {self.last_output}, exists = {os.path.exists(self.last_output) if self.last_output else False}")
        if self.last_output and os.path.exists(self.last_output):
            self.open_button.config(state="normal", style="TButton")
            print("Open Output button enabled")
        else:
            print("Open Output button remains disabled")
        self.root.update_idletasks()

# Run the GUI
if __name__ == "__main__":
    print("Starting main block")
    root = tk.Tk()
    print("Tk root created")
    app = VideoProcessorApp(root)
    print("App instance created")
    root.mainloop()
    print("Mainloop exited")
