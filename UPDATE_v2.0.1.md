# CCify Video v2.0.1 - Critical Fixes

## What Was Fixed

### 1. **Audio Extraction Timeout** ✅
**Problem**: Large video files were timing out during audio extraction after 60 seconds

**Solution**: 
- Increased default command timeout from 60s to 300s (5 minutes)
- Audio extraction timeout specifically set to 600s (10 minutes)
- Transcription timeout set to 1800s (30 minutes)

### 2. **Pre-Processing Options Menu** ✅
**Problem**: Tool started processing immediately without showing options

**Solution**: Added comprehensive pre-processing menu that shows:

```
File Information:
  Name: video.mp4
  Size: 123.45 MB
  Duration: 45.2 seconds (0.8 minutes)
  Resolution: 1920x1080
  Video Codec: h264
  Audio Codec: aac

PROCESSING OPTIONS
==================

Current Profile: balanced
  Model: base.en
  Language: auto
  Aggressive Audio: True
  Output Format: mp4
  Burn-in: False

What would you like to do?

[1] Use current settings (recommended)
[2] Customize this run
[0] Back
```

### 3. **Customization Menu** ✅
When selecting option [2], you now get detailed choices:

**Transcription Model:**
- [1] tiny.en - Fastest (~32x realtime)
- [2] base.en - Balanced (~16x realtime) [Current]
- [3] small.en - Better accuracy (~6x realtime)
- [4] medium.en - Best accuracy (~2x realtime)

**Output Format:**
- [1] MP4 (most compatible)
- [2] MKV (better subtitle support)

**Subtitle Type:**
- [1] Soft subtitles (can toggle on/off) [Default]
- [2] Burn-in subtitles (permanently embedded)
- [3] Both soft AND burn-in versions

**Audio Preprocessing:**
- [1] Standard (faster)
- [2] Aggressive (better quality, slower)

Then shows a summary and asks for confirmation before processing!

---

## How to Use

### Interactive Mode (Easiest):
```bash
ccify_cli.py
```

1. Select "Process Single File"
2. Drag and drop or type your video path
3. See file information
4. Choose [1] for default settings or [2] to customize
5. If customizing, select your preferences
6. Confirm and process!

### Command Line (Automated):
```bash
# Still works the same - no breaking changes
ccify_cli.py process video.mp4
ccify_cli.py process video.mp4 --burn-in --model base.en
```

---

## Timeline Expectations

For a typical video:

| Duration | Model | Expected Time |
|----------|-------|---------------|
| 1 minute | tiny.en | ~2 seconds |
| 1 minute | base.en | ~4 seconds |
| 1 minute | small.en | ~10 seconds |
| 1 minute | medium.en | ~30 seconds |
| 10 minutes | base.en | ~40 seconds |
| 60 minutes | base.en | ~4 minutes |

**Note**: First run downloads the model (~145MB for base.en), which adds 1-2 minutes one time only.

---

## What to Expect During Processing

```
PROCESSING
==========

This may take several minutes depending on video length...

Step 1/7: Probing media file...
  Duration: 45.20s
  Size: 123.45 MB
  Video: True, Audio: True

Step 2/7: Checking disk space...
  Sufficient space: 234.56 GB available (need 0.18 GB)

Step 3/7: Extracting audio...
  (This may take 1-2 minutes for large files)

Step 4/7: Transcribing with MLX Whisper...
  (This is the longest step - may take several minutes)

Step 5/7: Muxing soft subtitles...
  (Quick - usually under 30 seconds)

Step 6/7: Validating output...

Step 7/7: Finalizing...

✓ Processing complete in 180.23s (RTF: 4.00x)
```

---

## Troubleshooting

### Still Getting Timeouts?

If you have a very long video (>2 hours), you may need to:

1. **Use a faster model**: Switch to `tiny.en` or `base.en`
2. **Split the video**: Process in chunks
3. **Check system resources**: Close other apps

### File Not Found?

Use the drag-and-drop feature:
1. Type: `ccify_cli.py process ` (with trailing space)
2. Drag file from Finder
3. Press Enter

The tool automatically handles spaces and special characters!

---

## Testing

✅ Tested with small video (30 seconds) - works perfectly  
✅ Tested with medium video (5 minutes) - processing successful  
✅ Tested customization menu - all options working  
✅ Tested drag-and-drop with spaces in filename - works  
✅ All dependencies verified and working  

---

## Version Info

**Version**: 2.0.1  
**Date**: 2025-10-07  
**Changes**: Timeout fixes + Pre-processing options menu  

---

## Quick Reference

### Common Use Cases

**Quick Test:**
```bash
ccify_cli.py
# Select 1 (single file)
# Drag-and-drop file
# Select 1 (use defaults)
```

**Production Quality:**
```bash
ccify_cli.py
# Select 1 (single file)
# Drag-and-drop file
# Select 2 (customize)
# Choose: [4] medium.en model
# Choose: [2] Burn-in subtitles
# Confirm
```

**Fastest Processing:**
```bash
ccify_cli.py config --set-profile quick
ccify_cli.py process video.mp4
```

---

**Ready to process videos without timeout errors!** 🎉

Just run: `ccify_cli.py` or double-click `CCify_Video.command`
