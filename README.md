# KaraokeReady

A Python application for creating karaoke videos with synchronized lyrics. This tool allows you to:
- Create and edit LRC (lyrics) files
- Synchronize lyrics manually with audio
- Create karaoke videos with animated lyrics
- Remove vocals from songs using Spleeter
- Generate beautiful gradient backgrounds

## Features

- **Lyrics Creation**: Create LRC files from MP3 files with automatic timestamp generation
- **Manual Sync**: Synchronize lyrics manually by clicking as each line is sung
- **Karaoke Video**: Generate karaoke videos with animated lyrics and gradient backgrounds
- **Vocal Removal**: Option to remove vocals using Spleeter for better karaoke experience
- **User-Friendly Interface**: Simple and intuitive GUI with multiple tabs for different functions

## Requirements

- Python 3.8 or higher
- MoviePy
- ImageMagick
- Spleeter (optional, for vocal removal)
- Other dependencies listed in requirements.txt

## Installation

1. Clone the repository:
```bash
git clone https://github.com/Norrathian/Karaokeready.git
cd Karaokeready
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

3. Install ImageMagick:
- Download from: https://imagemagick.org/script/download.php
- During installation, ensure "Add to system PATH" is checked
- Restart your computer after installation

## Usage

1. Run the application:
```bash
python karaoke_app.py
```

2. Use the tabs to:
   - Create or edit LRC files
   - Manually sync lyrics with audio
   - Generate karaoke videos

## License

This project is licensed under the MIT License - see the LICENSE file for details. 