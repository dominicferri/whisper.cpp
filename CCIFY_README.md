# CCify Video v2.0 - Enterprise Video Captioning Tool

**AAA-Grade CLI Tool for Automated Video Captioning with MLX Whisper**

Optimized for Apple Silicon (M1/M2/M3)

---

## 🚀 Quick Start

### Installation Check
```bash
# Check if everything is installed
ccify_cli.py info --check
```

### Interactive Mode (Easiest)
```bash
# Launch the interactive menu
ccify_cli.py

# Or double-click
CCify_Video.command
```

### Process a Single Video
```bash
# Drag and drop a file or type the path
ccify_cli.py process video.mp4

# With specific options
ccify_cli.py process video.mp4 --burn-in --model base.en
```

### Batch Processing
```bash
# Process multiple files
ccify_cli.py batch *.mp4 --parallel --max-concurrent 2

# Continue on errors
ccify_cli.py batch video1.mp4 video2.mkv --continue-on-error
```

---

## ✨ Features

### Enterprise-Grade Reliability
- **Robust Path Handling**: Drag-and-drop from Finder, handles spaces and special characters
- **Smart Error Recovery**: Intelligent file suggestions when paths fail
- **Comprehensive Logging**: Detailed logs at `~/Downloads/CCify/logs/`
- **Graceful Interruption**: Ctrl+C handling with cleanup
- **Disk Space Checks**: Pre-flight validation before processing

### Processing Capabilities
- **Batch Processing**: Process multiple files with parallel execution
- **Multiple Formats**: MP4, MKV, AVI, MOV, WebM, and more
- **Soft Subtitles**: Embeddable SRT subtitles you can toggle on/off
- **Burn-in Subtitles**: Permanent captions embedded in video
- **Audio Preprocessing**: Aggressive noise reduction and normalization

### User Experience
- **Interactive Menu**: Beautiful terminal UI with numbered options
- **Configuration Profiles**: Quick, Balanced, and Quality presets
- **Persistent Settings**: Your preferences are saved automatically
- **Progress Tracking**: Real-time progress with ETA
- **Helpful Suggestions**: Smart error messages with actionable fixes

---

## 📋 System Requirements

### Required Dependencies
- **macOS**: 10.15+ (Optimized for Apple Silicon)
- **Python 3**: 3.9 or higher (installed at `/opt/homebrew/bin/python3`)
- **ffmpeg**: Latest version (installed via Homebrew)
- **mlx-whisper**: Python package for Apple Silicon

### Installation

All dependencies should already be installed. If not:

```bash
# Install Homebrew (if needed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install ffmpeg
brew install ffmpeg

# Install Python 3
brew install python3

# Install mlx-whisper
/opt/homebrew/bin/python3 -m pip install mlx-whisper
```

---

## 🎯 Usage Guide

### Interactive Mode

The easiest way to use CCify Video is through the interactive menu:

```bash
ccify_cli.py
```

**Menu Options:**
1. **Process Single File**: Drag-and-drop or type path
2. **Process Multiple Files**: Batch processing
3. **Configuration Wizard**: Change quality settings
4. **View Settings**: See current configuration
5. **System Info & Checks**: Verify dependencies
6. **Clean Temp Files**: Free up disk space
7. **Help**: Show usage guide

### Command Line Mode

#### Process Single Video
```bash
# Basic usage
ccify_cli.py process video.mp4

# With specific model
ccify_cli.py process video.mp4 --model medium.en

# Create burn-in version
ccify_cli.py process video.mp4 --burn-in

# Specify output format
ccify_cli.py process video.mp4 --format mkv

# Aggressive audio processing
ccify_cli.py process video.mp4 --aggressive

# Dry run (preview only)
ccify_cli.py process video.mp4 --dry-run
```

#### Batch Processing
```bash
# Process all MP4 files
ccify_cli.py batch *.mp4

# Parallel processing (2 files at once)
ccify_cli.py batch *.mp4 --parallel --max-concurrent 2

# Continue even if some files fail
ccify_cli.py batch *.mp4 --continue-on-error

# With specific settings
ccify_cli.py batch *.mp4 --model base.en --format mkv
```

#### Configuration
```bash
# Interactive configuration wizard
ccify_cli.py config --interactive

# Set a specific profile
ccify_cli.py config --set-profile balanced

# Show current settings
ccify_cli.py config --show
```

#### System Information
```bash
# Check all dependencies
ccify_cli.py info --check

# List available models
ccify_cli.py info --models
```

#### Maintenance
```bash
# Clean temporary files
ccify_cli.py clean --temp

# Skip confirmation prompt
ccify_cli.py clean --temp --yes
```

---

## ⚙️ Configuration

### Configuration File

Settings are stored in `~/.ccify_config.json`

### Profiles

Three preset profiles are available:

#### Quick (Fast Processing)
- Model: `tiny.en`
- Video Preset: `ultrafast`
- Best for: Quick drafts and testing
- Speed: ~32x realtime

#### Balanced (Recommended)
- Model: `base.en`
- Video Preset: `veryfast`  
- Best for: Most use cases
- Speed: ~16x realtime

#### Quality (Best Results)
- Model: `medium.en`
- Video Preset: `slow`
- Best for: Final production output
- Speed: ~2x realtime

### Available Models

| Model | Size | Speed | Accuracy | Use Case |
|-------|------|-------|----------|----------|
| `tiny` | 75MB | ~32x | Low | Quick drafts |
| `tiny.en` | 75MB | ~32x | Low | English drafts |
| `base` | 145MB | ~16x | Medium | General use |
| `base.en` | 145MB | ~16x | Medium | English general |
| `small` | 466MB | ~6x | Good | Better accuracy |
| `small.en` | 466MB | ~6x | Good | English accuracy |
| `medium` | 1.5GB | ~2x | Great | Production |
| `medium.en` | 1.5GB | ~2x | Great | English production |

**Note**: Models ending in `.en` are English-only and run faster.

---

## 🎨 Subtitle Styling

### Burn-in Subtitle Appearance

Customize how burned-in subtitles look:

```json
{
  "style": {
    "font_name": "Helvetica",
    "font_size": 40,
    "outline": 3,
    "margin_v": 40,
    "alignment": 2
  }
}
```

**Alignment Codes:**
- `1` = Bottom Left
- `2` = Bottom Center (Default)
- `3` = Bottom Right
- `5` = Middle Left
- `6` = Middle Center
- `7` = Middle Right
- `9` = Top Left
- `10` = Top Center
- `11` = Top Right

---

## 📊 Output Formats

### Supported Container Formats
- **MP4**: Soft subs with `mov_text` codec
- **MKV**: Soft subs with `srt` codec (recommended)
- **WebM**: Limited subtitle support (use sidecar VTT)

### Subtitle Formats
- **SRT**: Most compatible, works everywhere
- **VTT**: Web standard, good for HTML5 video
- **ASS**: Advanced styling, best for anime/complex subs

### Output Locations

All outputs are saved to `~/Downloads/CCify/`:

```
~/Downloads/CCify/
├── logs/                          # Processing logs
├── temp/                          # Temporary files (auto-cleaned)
├── video_name_CC.mp4             # Soft subtitle version
└── video_name_CC_burned.mp4      # Burn-in version (if requested)
```

---

## 🔧 Advanced Usage

### Drag and Drop

The tool intelligently handles drag-and-drop from macOS Finder:

1. Open Terminal
2. Type `ccify_cli.py process ` (with trailing space)
3. Drag video file from Finder
4. Press Enter

**Handles:**
- File paths with spaces
- Special characters
- Escaped paths from Terminal
- `file://` URIs

### Environment Variables

```bash
# Use custom config file
ccify_cli.py --config /path/to/custom_config.json process video.mp4

# Increase verbosity
ccify_cli.py -vvv process video.mp4

# Quiet mode (errors only)
ccify_cli.py -q process video.mp4
```

### Exit Codes

For scripting and automation:

| Code | Meaning | When It Happens |
|------|---------|----------------|
| 0 | Success | Operation completed successfully |
| 1 | Generic Error | Unexpected error occurred |
| 2 | Config Error | Configuration file issue |
| 3 | Dependency Error | Missing ffmpeg, Python, or mlx-whisper |
| 4 | Path Error | File not found or invalid path |
| 5 | Disk Space Error | Not enough disk space |
| 6 | Network Error | Model download failed |
| 7 | Transcription Error | MLX Whisper failed |
| 8 | Encoding Error | ffmpeg encoding failed |
| 9 | Validation Error | Output file is invalid |
| 10 | Interrupted | User pressed Ctrl+C |

### Scripting Example

```bash
#!/bin/bash

# Process all videos in a directory
for video in ~/Videos/*.mp4; do
    ccify_cli.py process "$video" --model base.en -q
    if [ $? -ne 0 ]; then
        echo "Failed to process: $video"
    fi
done
```

---

## 🐛 Troubleshooting

### File Not Found

**Problem**: Getting "File not found" errors

**Solutions:**
1. Use drag-and-drop instead of typing paths
2. Use absolute paths: `/Users/yourusername/Videos/file.mp4`
3. Escape spaces: `~/Videos/my\ video.mp4`
4. Use quotes: `~/Videos/"my video.mp4"`

The tool will suggest similar files if it can't find your input.

### Low Disk Space

**Problem**: "Insufficient disk space" error

**Solution:**
```bash
# Check available space
df -h ~/Downloads

# Clean temporary files
ccify_cli.py clean --temp --yes

# Estimate: You need ~1.5x the video file size
```

### Slow Processing

**Problem**: Transcription takes too long

**Solutions:**
1. Switch to faster model: `--model tiny.en`
2. Use Quick profile: `ccify_cli.py config --set-profile quick`
3. Disable aggressive preprocessing in config
4. Check Activity Monitor for other processes

### Model Download Issues

**Problem**: First run fails downloading models

**Solutions:**
1. Check internet connection
2. Retry with: `ccify_cli.py process video.mp4`
3. Models are cached after first download
4. Check firewall settings for Python

### Subtitle Sync Issues

**Problem**: Subtitles are out of sync

**Solutions:**
1. Use better model: `--model medium.en`
2. Enable aggressive audio preprocessing: `--aggressive`
3. Check if video has multiple audio tracks
4. Try re-encoding the video first

---

## 📚 Examples

### Common Workflows

#### Quick Test Run
```bash
# Fast processing with tiny model
ccify_cli.py process test.mp4 --model tiny.en --dry-run
ccify_cli.py process test.mp4 --model tiny.en
```

#### Production Quality
```bash
# Best quality for final output
ccify_cli.py config --set-profile quality
ccify_cli.py process final_video.mp4 --burn-in
```

#### Batch Convert All Videos
```bash
# Process entire directory in parallel
cd ~/Videos
ccify_cli.py batch *.mp4 \
    --parallel \
    --max-concurrent 2 \
    --model base.en \
    --continue-on-error
```

#### Create Both Soft and Hard Subs
```bash
# First create soft subs version
ccify_cli.py process video.mp4 --format mkv

# Then create burn-in version
ccify_cli.py process video.mp4 --burn-in
```

---

## 🎯 Best Practices

### Model Selection
- **Short videos (<5 min)**: Use `base.en` or `small.en`
- **Long videos (>1 hour)**: Use `tiny.en` or `base.en` for speed
- **Critical accuracy**: Use `medium.en` despite slower speed
- **Non-English**: Use models without `.en` suffix

### Format Selection
- **MP4 + Soft Subs**: Best for most use cases
- **MKV**: Better subtitle support, larger file
- **Burn-in**: When you can't toggle subs off
- **Both**: Use batch mode to create multiple versions

### Performance Tips
1. **Parallel Processing**: Use `--max-concurrent 2` on M1/M2
2. **Disk Space**: Keep 10GB+ free in ~/Downloads
3. **Temp Cleanup**: Run `ccify_cli.py clean --temp` regularly
4. **Model Caching**: First run downloads models (slow), subsequent runs are fast

---

## 📖 Technical Details

### Architecture

```
ccify_cli.py
├── Interactive Menu
│   ├── Single File Processing
│   ├── Batch Processing
│   ├── Configuration Wizard
│   └── System Information
│
├── CLI Commands
│   ├── process: Single file
│   ├── batch: Multiple files
│   ├── config: Settings management
│   ├── info: System checks
│   └── clean: Maintenance
│
├── Core Components
│   ├── PathValidator: Smart path handling
│   ├── FileProcessor: Main processing engine
│   ├── BatchProcessor: Multi-file handling
│   ├── ConfigManager: Settings persistence
│   ├── LogManager: Enterprise logging
│   ├── MediaProber: ffprobe integration
│   └── DependencyChecker: Validation
│
└── Integration
    ├── mlx_transcribe.py: Transcription backend
    ├── ffmpeg: Media processing
    └── ffprobe: Media inspection
```

### Processing Pipeline

```
Input File
    ↓
1. Validation (Path, Format, Disk Space)
    ↓
2. Media Probing (Duration, Codec, Resolution)
    ↓
3. Audio Extraction (16kHz mono WAV)
    ↓
4. Preprocessing (Optional: Aggressive filters)
    ↓
5. Transcription (MLX Whisper → SRT)
    ↓
6. Muxing (Soft subs) OR Burn-in (Hard subs)
    ↓
7. Validation (Output integrity check)
    ↓
8. Cleanup (Remove temp files)
    ↓
Output File(s)
```

### File Locations

| Path | Purpose |
|------|---------|
| `~/.ccify_config.json` | Configuration file |
| `~/Downloads/CCify/` | Output directory |
| `~/Downloads/CCify/temp/` | Temporary files |
| `~/Downloads/CCify/logs/` | Processing logs |

---

## 🆘 Getting Help

### In-App Help
```bash
# General help
ccify_cli.py --help

# Command-specific help
ccify_cli.py process --help
ccify_cli.py batch --help
ccify_cli.py config --help
```

### Interactive Help
```bash
# Launch menu and select option 7
ccify_cli.py
```

### Log Files

Processing logs are automatically saved with timestamps:

```bash
# View latest log
ls -lt ~/Downloads/CCify/logs/ | head -1

# Tail log in real-time
tail -f ~/Downloads/CCify/logs/ccify_*.log
```

---

## 📝 Version Information

**Version**: 2.0.0  
**Build Date**: 2025-10-07  
**Platform**: macOS (Apple Silicon Optimized)  
**Python**: 3.9+  
**Dependencies**: ffmpeg, mlx-whisper

---

## 🎉 Success Criteria

This tool meets AAA enterprise-grade standards:

✅ **Reliability**
- Zero uncaught exceptions
- Graceful error handling
- Meaningful exit codes
- Atomic file operations

✅ **Usability**
- Drag-and-drop support
- Interactive menu
- Smart path suggestions
- Comprehensive help

✅ **Performance**
- Parallel processing
- Progress tracking
- RTF metrics
- Efficient disk usage

✅ **Enterprise Features**
- Detailed logging
- Configuration profiles
- Batch processing
- Non-interactive mode

---

## 🔄 Changelog

### v2.0.0 (2025-10-07)
- Complete rewrite as enterprise-grade CLI tool
- Added interactive menu system
- Implemented configuration profiles (Quick, Balanced, Quality)
- Added batch processing with parallelism
- Intelligent path handling with drag-and-drop support
- Smart file suggestions when paths fail
- Comprehensive logging system
- Disk space checking before processing
- Progress tracking with real-time ETA
- Exit code standardization for scripting
- Dry-run mode for previewing operations
- Enhanced error messages with actionable fixes

### v1.0.0 (Previous)
- Original bash script implementation
- Basic video processing
- MLX Whisper integration

---

**Made with ❤️ for Apple Silicon**

For issues or questions, check the logs at `~/Downloads/CCify/logs/`
