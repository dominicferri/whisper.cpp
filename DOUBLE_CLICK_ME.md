# 🖱️ DOUBLE-CLICK TO USE!

## How to Use the .command Launcher

### **Just Double-Click!** 🎯

1. **Find the file:** `MLX_Transcribe.command`
2. **Double-click it** - Terminal opens automatically!
3. **Choose from the menu:**
   - Transcribe single files
   - MAX POWER mode
   - Create subtitles
   - Batch process folders
   - And more!

### First Time Setup (macOS Security)

**The first time you double-click**, macOS might say "cannot be opened because it is from an unidentified developer."

**Fix it:**
1. Right-click (or Control+click) on `MLX_Transcribe.command`
2. Select "Open"
3. Click "Open" again in the dialog
4. ✅ It will work from now on!

**Or use Terminal command:**
```bash
xattr -d com.apple.quarantine MLX_Transcribe.command
```

## Menu Options

When you double-click, you'll see:

### 1️⃣ Transcribe a single file
- Uses your CURRENT settings (model, outputs, Aggressive, VAD, Diarization, language, retries)
- Drag & drop any audio/video file
- Fast and simple!

### 2️⃣ Configure advanced options
- Model: tiny/tiny.en/base/base.en/small/small.en/medium/medium.en
- Aggressive: stronger denoise/normalization before transcription
- VAD (silence removal): trims non-speech using threshold/start/stop tuning
- Diarization (stereo): splits left/right channels as Speaker A/B and merges
- Language: set a language or leave blank for auto-detect; optional fallbacks if auto-detect is weak
- Retries: number of times to retry failed operations
- Outputs: choose TXT/SRT/VTT/JSON

### 3️⃣ Batch Process Folder
- Apply CURRENT settings to every .mp4 in a folder
- Drag & drop the folder
- Great for processing whole video libraries

### 4️⃣ Quick Subtitles (SRT + VTT)
- Temporarily forces outputs to SRT + VTT for a single file
- Other CURRENT settings still apply (model, Aggressive, VAD, Diarization, language, retries)

### 5️⃣ Show Help
- Shows the full CLI help from mlx_transcribe.py
- Learn all flags and usage patterns

### 6️⃣ Custom Command
- Type your own command
- Full control over options
- For advanced users

### 7️⃣ Run Smoke Test
- Verifies your environment end-to-end:
  - Checks ffmpeg is installed
  - Runs a VAD preprocessing + quick transcription on a sample
  - Builds a stereo test file to exercise diarization path

### 8️⃣ Exit
- Close the app

## Quick Tips 💡

✨ **Drag & Drop:** When prompted, just drag your file/folder into the Terminal window!

✨ **Video Files:** Works with MP4, MKV, AVI, MOV, and more!

✨ **Audio Files:** MP3, WAV, M4A, FLAC, OGG, etc.

✨ **Batch Processing:** Drop a folder to process all videos at once!

✨ **Fast:** Runs at 77x realtime on your M4 Mac!

## What You Get

After transcription, you'll find in the same folder:
- `filename.txt` - Plain text transcription
- `filename.srt` - SRT subtitles
- `filename.vtt` - WebVTT subtitles  
- `filename.json` - Full metadata
- `filename-optimized.wav` - Optimized audio

## Examples

### Add Subtitles to a Movie
1. Double-click `MLX_Transcribe.command`
2. Choose option **3** (Create Subtitles)
3. Drag & drop your video file
4. Wait a few seconds ⚡
5. Get perfect SRT subtitles!

### Transcribe Multiple Videos
1. Double-click `MLX_Transcribe.command`
2. Choose option **4** (Batch Process)
3. Drag & drop the folder with videos
4. All videos get transcribed!

### Quick Single File
1. Double-click `MLX_Transcribe.command`
2. Choose option **1** (Single File)
3. Drag & drop your file
4. Done! ✅

## Troubleshooting

**Terminal won't open?**
- Right-click → Open (first time only)
- Or run: `xattr -d com.apple.quarantine MLX_Transcribe.command`

**Command not found?**
- Make sure you're in the correct folder
- The .command file must be in the same folder as mlx_transcribe.py

**Python errors?**
- MLX Whisper should be installed
- Run: `pip3 install mlx-whisper`

## Manual Use (Alternative)

If you prefer command line:
```bash
# Navigate to folder
cd ~/whisper.cpp

# Run directly
./mlx_transcribe.py your_file.mp4 --srt
```

---

## 🚀 That's It!

**Just double-click `MLX_Transcribe.command` and you're ready to transcribe!**

Your M4 Mac + MLX = Transcription Beast! 💪
