#!/bin/bash

# Audio preprocessing script for whisper.cpp
# This script optimizes audio files for transcription by:
# - Converting to 16-bit PCM WAV at 16kHz (required by whisper.cpp)
# - Applying noise reduction (afftdn filter)
# - Dynamic audio normalization (dynaudnorm)
# - Loudness normalization
# - Speech-focused EQ (highpass/lowpass filters)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if input file is provided
if [ "$#" -lt 1 ]; then
    echo "Usage: $0 <input_audio_file> [output_file]"
    echo ""
    echo "This script optimizes audio for whisper.cpp transcription."
    echo "If no output file is specified, it will be saved as <input>-optimized.wav"
    echo ""
    echo "Example:"
    echo "  $0 input.mp3"
    echo "  $0 input.mp3 output.wav"
    exit 1
fi

INPUT_FILE="$1"
OUTPUT_FILE="${2:-}"

# Check if input file exists
if [ ! -f "$INPUT_FILE" ]; then
    print_error "Input file not found: $INPUT_FILE"
    exit 1
fi

# Generate output filename if not provided
if [ -z "$OUTPUT_FILE" ]; then
    BASENAME=$(basename "$INPUT_FILE" | sed 's/\.[^.]*$//')
    OUTPUT_FILE="${BASENAME}-optimized.wav"
fi

print_info "Processing: $INPUT_FILE"
print_info "Output: $OUTPUT_FILE"

# Audio preprocessing pipeline
# - highpass=f=100: Remove low-frequency rumble below 100 Hz
# - lowpass=f=8000: Remove high frequencies above 8 kHz (speech is mostly below this)
# - afftdn=nf=-25: Noise reduction (adaptive FFT denoising)
# - dynaudnorm: Dynamic audio normalization (makes quiet parts louder)
# - loudnorm: EBU R128 loudness normalization for consistent volume
# - ar 16000: Resample to 16 kHz (required by whisper.cpp)
# - ac 1: Convert to mono (required by whisper.cpp)
# - c:a pcm_s16le: 16-bit PCM encoding (required by whisper.cpp)

ffmpeg -hide_banner -y -i "$INPUT_FILE" \
    -af "highpass=f=100,lowpass=f=8000,afftdn=nf=-25,dynaudnorm,loudnorm=I=-18:LRA=7:TP=-2" \
    -ar 16000 \
    -ac 1 \
    -c:a pcm_s16le \
    "$OUTPUT_FILE"

if [ $? -eq 0 ]; then
    print_info "Audio preprocessing completed successfully!"
    print_info "Optimized file: $OUTPUT_FILE"
    echo ""
    print_info "You can now transcribe with:"
    echo "  ./build/bin/whisper-cli -m models/ggml-base.en.bin -f \"$OUTPUT_FILE\""
else
    print_error "Audio preprocessing failed!"
    exit 1
fi
