# Subtitle Troubleshooting Guide

## ✅ Your Subtitles ARE There!

Your video has subtitles embedded, but they might not show by default. Here's how to enable them in different players:

---

## 🎬 How to Enable Subtitles in Different Players

### **QuickTime Player (macOS)**
1. Open your video in QuickTime
2. Go to **View** menu → **Subtitles** → **English**
3. Or press **Command + Option + S** to toggle subtitles

**Note**: QuickTime shows subtitles but may need you to enable them manually.

### **VLC Media Player** (Most Reliable)
1. Open video in VLC
2. Go to **Subtitle** menu → **Sub Track** → **Track 1 - English**
3. Or press **Command + L** to cycle through subtitle tracks
4. Subtitles should show automatically if marked as default

### **IINA** (macOS - Best Option)
1. Open video in IINA
2. Subtitles should show automatically
3. If not, press **I** key to toggle subtitles
4. Or click the subtitle icon in the player controls

### **Safari/Web Browser**
1. Play video in Safari
2. Click the **CC** button in video controls
3. Select **English**

---

## 🔧 Quick Fix: Re-process with Default Subtitle Track

I've updated the tool to mark subtitles as "default" so they show automatically. 

### Option 1: Re-process Your Video (Recommended)
```bash
ccify_cli.py process "~/Desktop/Kempler\ family\ video.mp4"
```

This will:
- Create a new file with subtitles marked as default
- Subtitles will show automatically in most players
- Takes the same amount of time (~7-8 minutes)

### Option 2: Enable Existing Subtitles Manually
Just use the player controls above to enable the subtitle track.

---

## 🎯 What Changed in v2.0.2

**NEW**: Subtitles are now marked as:
- `default` disposition - Shows automatically
- `language=eng` - Identified as English
- `title=English` - Labeled for easy identification

**Command added**:
```
-disposition:s:0 default
```

This tells the player to enable the subtitle track by default.

---

## 📊 Verify Subtitles Are There

Run this command to check:
```bash
ffprobe -v quiet -print_format json -show_streams "~/Downloads/CCify/Kempler family video_CC.mp4" | grep -A 10 subtitle
```

You should see:
```json
"codec_type": "subtitle",
"codec_name": "mov_text",
"disposition": {
  "default": 1
}
```

---

## 🎬 Best Player Recommendations

For the best subtitle experience:

1. **IINA** (Free, Open Source, macOS)
   - Download: https://iina.io
   - Best subtitle support
   - Shows subtitles automatically
   - Highly recommended!

2. **VLC** (Free, Cross-platform)
   - Download: https://www.videolan.org
   - Excellent compatibility
   - Manual subtitle toggle needed sometimes

3. **QuickTime** (Built-in)
   - Works but requires manual enable
   - View → Subtitles → English

---

## 🔄 Re-process with New Default Settings

Want to re-process so subtitles show automatically everywhere?

```bash
# Quick re-process
ccify_cli.py

# Select option 1 (Process Single File)
# Drag and drop: ~/Desktop/Kempler\ family\ video.mp4
# Select option 1 (Use current settings)
# Wait ~7 minutes
# New file will have subtitles on by default!
```

---

## 📝 Current File Status

**Your existing file:**
- Location: `~/Downloads/CCify/Kempler family video_CC.mp4`
- Subtitles: ✅ Embedded (mov_text/tx3g codec)
- Default: ❌ Not set as default (old version)
- **Solution**: Enable manually in player OR re-process

**After re-processing with v2.0.2:**
- Subtitles: ✅ Embedded
- Default: ✅ Set as default
- **Result**: Shows automatically in most players!

---

## 🎯 Quick Test

### Test in VLC:
1. Install VLC if you don't have it
2. Open your video
3. Press **Command + L** to cycle subtitle tracks
4. You should see the English subtitles appear!

### Test in IINA:
1. Install IINA (https://iina.io)
2. Open your video
3. Subtitles should appear automatically!
4. Press **I** to toggle if needed

---

## 💡 Pro Tip: Create Both Versions

Want subtitles you can't turn off? Create a burn-in version:

```bash
ccify_cli.py process "video.mp4" --burn-in
```

This creates a second version with subtitles permanently embedded in the video image. Can't be toggled off, but always visible!

---

## 🆘 Still Not Working?

### Check the subtitle file directly:
```bash
ls -lh ~/Downloads/CCify/temp/*.srt
```

You should see a `.srt` file with your subtitles. You can:
1. Open it in a text editor to verify content
2. Use it as a separate subtitle file
3. Drag it into VLC along with your video

### Alternative: Use Sidecar Subtitles
If embedded subtitles aren't working, rename the .srt file to match your video:
```bash
# If your video is: video.mp4
# Rename subtitle to: video.srt
# Place in same folder
# Most players will auto-load it!
```

---

## ✅ Summary

**Your subtitles ARE there!** They're just not set as default.

**Quick fixes:**
1. ⚡ Enable in player (View → Subtitles → English)
2. 🔄 Re-process with updated tool (subtitles default on)
3. 📂 Use IINA player (best subtitle support)

**Next video:** Will have subtitles on by default automatically! 🎉

---

**Updated**: v2.0.2 - Subtitles now default enabled
**Previous**: v2.0.1 - Subtitles embedded but not default
