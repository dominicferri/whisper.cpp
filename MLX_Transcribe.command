#!/bin/bash

# MLX Transcribe Launcher
# Double-click this file to launch the transcription tool!

# Get the directory where this script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# Clear screen and show banner
clear
cat << 'EOF'

╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║        🚀 MAX POWER MLX WHISPER TRANSCRIPTION TOOL 🚀         ║
║                                                                ║
║              For Audio & Video - M4 Optimized                  ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝

EOF

echo "📍 Working directory: $DIR"
echo ""

# -----------------------------
# Defaults / Session Settings
# -----------------------------
# (defaults)
MODEL="base.en"            # tiny, tiny.en, base, base.en, small, small.en, medium, medium.en
AGGRESSIVE="0"             # 1 = enable aggressive preprocessing
VAD="0"                     # 1 = enable VAD (silence removal)
VAD_THRESHOLD="-40"        # dB threshold for VAD
VAD_START="0.10"           # seconds of leading silence to trim when speech starts
VAD_STOP="0.10"            # seconds of trailing silence to trim when speech stops
DIARIZE="0"                # 1 = split stereo into speakers A/B
RETRIES="1"                # retry count for operations
LANG=""                    # language code (empty = auto-detect)
LANG_FALLBACKS=""          # comma-separated fallbacks (e.g. en,es,fr)
OUT_TXT="1"                # which formats to save by default
OUT_SRT="0"
OUT_VTT="0"
OUT_JSON="0"

# Load persisted settings if present
CFG_FILE="$DIR/.mlx_transcribe_config"
if [ -f "$CFG_FILE" ]; then
    # shellcheck disable=SC1090
    . "$CFG_FILE"
fi

# -----------------------------
# Helpers
# -----------------------------
show_settings() {
    echo "Current settings:"
    echo "  Model                : $MODEL"
    echo "  Aggressive           : $( [ "$AGGRESSIVE" = "1" ] && echo ON || echo OFF )"
    echo "  VAD                  : $( [ "$VAD" = "1" ] && echo ON || echo OFF ) (thresh=${VAD_THRESHOLD}dB, start=${VAD_START}s, stop=${VAD_STOP}s)"
    echo "  Diarize (stereo)     : $( [ "$DIARIZE" = "1" ] && echo ON || echo OFF )"
    echo "  Retries              : $RETRIES"
    echo "  Language             : ${LANG:-auto-detect}"
    echo "  Language fallbacks   : ${LANG_FALLBACKS:-none}"
    echo "  Outputs              : $( [ "$OUT_TXT" = "1" ] && echo "TXT " )$( [ "$OUT_SRT" = "1" ] && echo "SRT " )$( [ "$OUT_VTT" = "1" ] && echo "VTT " )$( [ "$OUT_JSON" = "1" ] && echo "JSON" )"
    echo ""
}

# Build and run command for a single file using current toggles
run_transcribe_for_file() {
    local file="$1"
    shift
    # Optional overrides via env vars for this call only:
    local override_aggr="$OVERRIDE_AGGR"    # "0" or "1" or empty
    local override_out_all="$OVERRIDE_OUT_ALL"  # "1" -> --all-formats
    local override_out_srtvtt="$OVERRIDE_OUT_SRTVTT"  # "1" -> --srt --vtt

    local -a CMD_ARGS=("python3" "mlx_transcribe.py" "$file" "-m" "$MODEL" "--retries" "$RETRIES")

    # Language options
    if [ -n "$LANG" ]; then CMD_ARGS+=("-l" "$LANG"); fi
    if [ -n "$LANG_FALLBACKS" ]; then CMD_ARGS+=("--language-fallbacks" "$LANG_FALLBACKS"); fi

    # Aggressive
    local use_aggr="$AGGRESSIVE"
    if [ -n "$override_aggr" ]; then use_aggr="$override_aggr"; fi
    if [ "$use_aggr" = "1" ]; then CMD_ARGS+=("--aggressive"); fi

    # VAD
    if [ "$VAD" = "1" ]; then
        CMD_ARGS+=("--vad" "--vad-threshold" "$VAD_THRESHOLD" "--vad-start-silence" "$VAD_START" "--vad-stop-silence" "$VAD_STOP")
    fi

    # Diarization
    if [ "$DIARIZE" = "1" ]; then CMD_ARGS+=("--diarize-stereo"); fi

    # Outputs
    if [ "$override_out_all" = "1" ]; then
        CMD_ARGS+=("--all-formats")
    elif [ "$override_out_srtvtt" = "1" ]; then
        CMD_ARGS+=("--srt" "--vtt")
    else
        # Respect explicit toggles; if none on, python defaults to TXT
        [ "$OUT_TXT" = "1" ] && CMD_ARGS+=("--txt")
        [ "$OUT_SRT" = "1" ] && CMD_ARGS+=("--srt")
        [ "$OUT_VTT" = "1" ] && CMD_ARGS+=("--vtt")
        [ "$OUT_JSON" = "1" ] && CMD_ARGS+=("--json")
    fi

    echo "Running: ${CMD_ARGS[*]}"
    "${CMD_ARGS[@]}"
}

configure_options_menu() {
    while true; do
        clear
        echo "⚙️  Configure Advanced Options"
        echo ""
        show_settings
        echo "Select setting to change:"
        echo "  1) Model            – Choose tiny/tiny.en/base/base.en/small/small.en/medium/medium.en"
        echo "  2) Aggressive       – Toggle aggressive preprocessing (strong denoise, normalization)"
        echo "  3) VAD              – Toggle / tune silence removal (threshold/start/stop)"
        echo "  4) Diarize (stereo) – Toggle stereo speaker split (Speaker A/B)"
        echo "  5) Language         – Set language code or leave empty for auto; optional fallbacks"
        echo "  6) Retries          – Set retry count for operations"
        echo "  7) Outputs          – Toggle TXT / SRT / VTT / JSON"
        echo "  8) Save (Persist)   – Save current settings for next runs"
        echo "  9) Reset Defaults   – Reset to built-in defaults and remove saved config"
        echo "  0) Back"
        echo ""
        read -p "Enter choice (0-9): " opt
        case "$opt" in
            1)
                echo "Enter model (tiny, tiny.en, base, base.en, small, small.en, medium, medium.en):"
                read -r val
                [ -n "$val" ] && MODEL="$val"
                ;;
            2)
                if [ "$AGGRESSIVE" = "1" ]; then AGGRESSIVE="0"; else AGGRESSIVE="1"; fi
                ;;
            3)
                if [ "$VAD" = "1" ]; then
                    echo "VAD currently ON. Toggle off? (y/N)"
                    read -r yn; [ "$yn" = "y" ] || [ "$yn" = "Y" ] && VAD="0"
                else
                    VAD="1"
                fi
                if [ "$VAD" = "1" ]; then
                    echo "Enter VAD threshold in dB (current: $VAD_THRESHOLD, typical: -40):"; read -r t; [ -n "$t" ] && VAD_THRESHOLD="$t"
                    echo "Enter VAD start silence seconds (current: $VAD_START):"; read -r s; [ -n "$s" ] && VAD_START="$s"
                    echo "Enter VAD stop silence seconds (current: $VAD_STOP):"; read -r e; [ -n "$e" ] && VAD_STOP="$e"
                fi
                ;;
            4)
                if [ "$DIARIZE" = "1" ]; then DIARIZE="0"; else DIARIZE="1"; fi
                ;;
            5)
                echo "Enter language code (e.g., en, es, fr) or leave blank for auto-detect:"
                read -r LVAL; LANG="$LVAL"
                echo "Enter comma-separated language fallbacks (e.g., en,es,fr) or leave blank:"
                read -r FVAL; LANG_FALLBACKS="$FVAL"
                ;;
            6)
                echo "Enter retry count (current: $RETRIES):"
                read -r r; [ -n "$r" ] && RETRIES="$r"
                ;;
            7)
                echo "Toggle outputs (1=on, 0=off). Leave blank to keep current."
                echo -n "TXT (current $OUT_TXT): "; read -r a; [ -n "$a" ] && OUT_TXT="$a"
                echo -n "SRT (current $OUT_SRT): "; read -r b; [ -n "$b" ] && OUT_SRT="$b"
                echo -n "VTT (current $OUT_VTT): "; read -r c; [ -n "$c" ] && OUT_VTT="$c"
                echo -n "JSON (current $OUT_JSON): "; read -r d; [ -n "$d" ] && OUT_JSON="$d"
                ;;
            8)
                # Save to config
                {
                    echo "MODEL=$MODEL"
                    echo "AGGRESSIVE=$AGGRESSIVE"
                    echo "VAD=$VAD"
                    echo "VAD_THRESHOLD=$VAD_THRESHOLD"
                    echo "VAD_START=$VAD_START"
                    echo "VAD_STOP=$VAD_STOP"
                    echo "DIARIZE=$DIARIZE"
                    echo "RETRIES=$RETRIES"
                    printf "LANG=%q\n" "$LANG"
                    printf "LANG_FALLBACKS=%q\n" "$LANG_FALLBACKS"
                    echo "OUT_TXT=$OUT_TXT"
                    echo "OUT_SRT=$OUT_SRT"
                    echo "OUT_VTT=$OUT_VTT"
                    echo "OUT_JSON=$OUT_JSON"
                } > "$CFG_FILE"
                echo "Saved settings to $CFG_FILE"
                read -p "Press Enter to continue..."
                ;;
            9)
                # Reset defaults and remove config
                MODEL="base.en"; AGGRESSIVE="0"; VAD="0"; VAD_THRESHOLD="-40"; VAD_START="0.10"; VAD_STOP="0.10";
                DIARIZE="0"; RETRIES="1"; LANG=""; LANG_FALLBACKS=""; OUT_TXT="1"; OUT_SRT="0"; OUT_VTT="0"; OUT_JSON="0";
                [ -f "$CFG_FILE" ] && rm -f "$CFG_FILE"
                echo "Settings reset to defaults. Removed $CFG_FILE if it existed."
                read -p "Press Enter to continue..."
                ;;
            0)
                break
                ;;
            *) ;;
        esac
    done
}

# Function to show menu
show_menu() {
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "What would you like to do? (details below each option)"
    echo ""
    echo "  1) Transcribe a single file"
    echo "     - Uses CURRENT settings (model, outputs, Aggressive, VAD, Diarize, language, retries)"
    echo "     - You choose the file via drag & drop"
    echo ""
    echo "  2) Configure advanced options"
    echo "     - Toggle Aggressive preprocessing (strong denoise, normalization)"
    echo "     - Enable/tune VAD (silence removal): threshold/start/stop"
    echo "     - Enable Diarization (stereo split: Speaker A/B)"
    echo "     - Set language or auto-detect + fallbacks"
    echo "     - Choose outputs (TXT/SRT/VTT/JSON) and retry count"
    echo ""
    echo "  3) Batch process all MP4 files in a folder"
    echo "     - Applies CURRENT settings to every .mp4 in the chosen folder"
    echo ""
    echo "  4) Quick: Create subtitles (SRT + VTT) for a single file"
    echo "     - Temporarily uses SRT + VTT outputs"
    echo "     - Other CURRENT settings (model, Aggressive, VAD, Diarize, language, retries) still apply"
    echo ""
    echo "  5) Show help / all CLI options"
    echo "     - Prints mlx_transcribe.py --help with the full flag list"
    echo ""
    echo "  6) Custom command (type your own)"
    echo "     - Run a manual command line (advanced)"
    echo ""
    echo "  7) Run smoke test (ffmpeg/VAD/diarization)"
    echo "     - Verifies ffmpeg is installed"
    echo "     - Tests VAD preprocessing and a quick transcript"
    echo "     - Tests diarization by creating a stereo file and transcribing"
    echo ""
    echo "  8) Exit"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
}

run_smoke_test() {
    echo "🔎 Running smoke test..."
    local ok=1

    # Check ffmpeg
    if ! command -v ffmpeg >/dev/null 2>&1; then
        echo "❌ ffmpeg not found. Install with: brew install ffmpeg"
        ok=0
    else
        echo "✅ ffmpeg found"
    fi

    # VAD path test
    if [ -f "samples/jfk.wav" ]; then
        echo "→ Testing VAD on samples/jfk.wav"
        python3 mlx_transcribe.py samples/jfk.wav --vad --vad-threshold -38 -m tiny.en -q -o smoke_vad >/dev/null 2>&1
        if [ $? -eq 0 ]; then
            echo "✅ VAD preprocessing + transcription path OK (output: smoke_vad.txt)"
        else
            echo "❌ VAD test failed"
            ok=0
        fi
    else
        echo "⚠ samples/jfk.wav not found; skipping VAD test"
    fi

    # Diarization path test
    if [ -f "samples/jfk.wav" ]; then
        echo "→ Building stereo test file from samples/jfk.wav"
        ffmpeg -hide_banner -loglevel error -y -i samples/jfk.wav -ac 2 -ar 16000 -c:a pcm_s16le smoke_stereo.wav
        echo "→ Testing diarization on stereo audio"
        python3 mlx_transcribe.py smoke_stereo.wav --diarize-stereo -m tiny.en -q -o smoke_dz >/dev/null 2>&1
        if [ $? -eq 0 ]; then
            echo "✅ Diarization path OK (output: smoke_dz.txt)"
        else
            echo "❌ Diarization test failed"
            ok=0
        fi
    fi

    if [ $ok -eq 1 ]; then
        echo "🎉 Smoke test PASSED"
    else
        echo "⚠ Some checks FAILED"
    fi
    read -p "Press Enter to continue..."
}

# Function to get file path
get_file() {
    echo "Drag and drop your file here, then press Enter:"
    read -r filepath
    # Remove quotes and escape spaces
    filepath=$(echo "$filepath" | sed "s/^['\"]//;s/['\"]$//")
    echo "$filepath"
}

# Function to get folder path
get_folder() {
    echo "Drag and drop the folder here, then press Enter:"
    read -r folderpath
    # Remove quotes and escape spaces
    folderpath=$(echo "$folderpath" | sed "s/^['\"]//;s/['\"]$//")
    echo "$folderpath"
}

# Main loop
while true; do
    show_settings
    show_menu
    read -p "Enter your choice (1-8): " choice
    echo ""
    
    case $choice in
        1)
            echo "🎯 TRANSCRIBE SINGLE FILE (uses CURRENT settings)"
            echo ""
            filepath=$(get_file)
            if [ -f "$filepath" ]; then
                echo ""
                echo "Processing: $filepath"
                echo ""
                OVERRIDE_AGGR="" OVERRIDE_OUT_ALL="" OVERRIDE_OUT_SRTVTT="" \
                run_transcribe_for_file "$filepath"
                echo ""
                echo "✅ Done! Files saved in: $DIR"
            else
                echo "❌ File not found: $filepath"
            fi
            echo ""
            read -p "Press Enter to continue..."
            clear
            ;;
            
        2)
            configure_options_menu
            clear
            ;;
            
        3)
            echo "📁 BATCH PROCESS FOLDER (uses CURRENT settings)"
            echo ""
            folderpath=$(get_folder)
            if [ -d "$folderpath" ]; then
                echo ""
                echo "Processing all MP4 files in: $folderpath"
                echo ""
                for f in "$folderpath"/*.mp4; do
                    [ -f "$f" ] || continue
                    echo "---> $f"
                    OVERRIDE_AGGR="" OVERRIDE_OUT_ALL="" OVERRIDE_OUT_SRTVTT="" \
                    run_transcribe_for_file "$f"
                    echo ""
                done
                echo "✅ Done! All outputs saved in: $DIR"
            else
                echo "❌ Folder not found: $folderpath"
            fi
            echo ""
            read -p "Press Enter to continue..."
            clear
            ;;
            
        4)
            echo "📹 QUICK SUBTITLES (SRT + VTT) for a single file"
            echo ""
            filepath=$(get_file)
            if [ -f "$filepath" ]; then
                echo ""
                echo "Creating subtitles for: $filepath"
                echo ""
                OVERRIDE_AGGR="" OVERRIDE_OUT_ALL="" OVERRIDE_OUT_SRTVTT="1" \
                run_transcribe_for_file "$filepath"
                echo ""
                echo "✅ Done! Subtitles saved in: $DIR"
            else
                echo "❌ File not found: $filepath"
            fi
            echo ""
            read -p "Press Enter to continue..."
            clear
            ;;
            
        5)
            echo "📖 HELP & OPTIONS (mlx_transcribe.py --help)"
            echo ""
            python3 mlx_transcribe.py --help
            echo ""
            read -p "Press Enter to continue..."
            clear
            ;;
            
        6)
            echo "⌨️  CUSTOM COMMAND"
            echo ""
            echo "Examples of useful flags:"
            echo "  -m medium.en --aggressive --vad --vad-threshold -38 --diarize-stereo --srt --vtt --retries 2"
            echo ""
            read -p "Enter your command (or 'back' to return): " custom_cmd
            if [ "$custom_cmd" != "back" ]; then
                echo ""
                eval "python3 mlx_transcribe.py $custom_cmd"
                echo ""
                read -p "Press Enter to continue..."
            fi
            clear
            ;;
            
        7)
            run_smoke_test
            ;;
        8)
            echo "👋 Goodbye!"
            exit 0
            ;;
            
        *)
            echo "❌ Invalid choice. Please enter 1-8."
            sleep 2
            clear
            ;;
    esac
done
