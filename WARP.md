# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Overview

whisper.cpp is a high-performance C/C++ implementation of OpenAI's Whisper automatic speech recognition (ASR) model. On Apple Silicon, it leverages Metal for GPU acceleration and can use Core ML for the encoder to achieve significant performance improvements.

## Building the Project

### Standard Build (with Metal GPU acceleration on macOS)

```bash
# Build with Metal support (automatic on macOS)
cmake -B build
cmake --build build -j --config Release
```

### Build with Core ML Support (recommended for Apple Silicon)

Core ML can accelerate the encoder inference significantly (3x+ faster) on Apple Silicon:

```bash
# Build with Core ML support
cmake -B build -DWHISPER_COREML=1
cmake --build build -j --config Release
```

**Note**: After building with Core ML, you need to generate Core ML models separately (see Model Management below).

### Other Build Options

```bash
# Build with OpenBLAS for CPU acceleration
cmake -B build -DGGML_BLAS=1
cmake --build build -j --config Release

# Build with SDL2 for streaming examples
cmake -B build -DWHISPER_SDL2=ON
cmake --build build -j --config Release

# Build with FFmpeg support (Linux only)
cmake -B build -DWHISPER_FFMPEG=yes
cmake --build build -j --config Release

# Disable GPU (CPU-only)
cmake -B build -DGGML_METAL=OFF
cmake --build build -j --config Release
```

### Quick Build via Makefile

```bash
# Quick build using Makefile wrapper
make build

# Download model and run on samples
make base.en
```

## Model Management

### Downloading Models

Models are stored in the custom ggml format in the `models/` directory:

```bash
# Download a specific model
./models/download-ggml-model.sh base.en
./models/download-ggml-model.sh small
./models/download-ggml-model.sh medium

# Available models: tiny.en, tiny, base.en, base, small.en, small, 
#                   medium.en, medium, large-v1, large-v2, large-v3, large-v3-turbo
```

### Generating Core ML Models (macOS only)

For Apple Silicon with Core ML support:

```bash
# Install Python dependencies first
pip install ane_transformers openai-whisper coremltools

# Generate Core ML model (creates models/ggml-base.en-encoder.mlmodelc)
./models/generate-coreml-model.sh base.en
```

The Core ML model is automatically detected and used when running inference if built with `-DWHISPER_COREML=1`.

### Model Quantization

Quantize models to reduce memory usage and improve performance:

```bash
# Quantize a model (Q5_0 method)
./build/bin/quantize models/ggml-base.en.bin models/ggml-base.en-q5_0.bin q5_0

# Use quantized model
./build/bin/whisper-cli -m models/ggml-base.en-q5_0.bin -f samples/jfk.wav
```

## Running Transcription

### Basic Usage

The main CLI tool is `whisper-cli` (located at `build/bin/whisper-cli`):

```bash
# Transcribe a single audio file
./build/bin/whisper-cli -f samples/jfk.wav

# Specify model
./build/bin/whisper-cli -m models/ggml-base.en.bin -f samples/jfk.wav

# Use multiple threads
./build/bin/whisper-cli -m models/ggml-base.en.bin -f samples/jfk.wav -t 8

# Auto-detect language
./build/bin/whisper-cli -m models/ggml-base.bin -f samples/jfk.wav -l auto
```

### Output Formats

```bash
# Output as text file
./build/bin/whisper-cli -m models/ggml-base.en.bin -f samples/jfk.wav -otxt

# Output as SRT subtitles
./build/bin/whisper-cli -m models/ggml-base.en.bin -f samples/jfk.wav -osrt

# Output as VTT subtitles
./build/bin/whisper-cli -m models/ggml-base.en.bin -f samples/jfk.wav -ovtt

# Output as JSON
./build/bin/whisper-cli -m models/ggml-base.en.bin -f samples/jfk.wav -oj

# Multiple formats at once
./build/bin/whisper-cli -m models/ggml-base.en.bin -f samples/jfk.wav -otxt -osrt -ovtt
```

### Audio Format Requirements

whisper.cpp requires 16-bit WAV files at 16kHz sample rate. Convert audio using ffmpeg:

```bash
# Convert any audio format to compatible WAV
ffmpeg -i input.mp3 -ar 16000 -ac 1 -c:a pcm_s16le output.wav
```

## Testing

### Running Tests

```bash
# Run CTest suite (requires models in models/for-tests-*.bin)
cd build
ctest

# Run specific test
ctest -R test-whisper-cli-tiny

# Run integration tests
cd tests
./run-tests.sh base.en 4  # model name, threads
```

### Manual Testing

```bash
# Quick test with sample audio
./build/bin/whisper-cli -m models/ggml-base.en.bin -f samples/jfk.wav

# Benchmark performance
./build/bin/whisper-bench -m models/ggml-base.en.bin
```

## Architecture Overview

### Core Components

- **`src/whisper.cpp` & `include/whisper.h`**: Main library implementation with C API
- **`src/whisper-arch.h`**: Tensor naming and architecture definitions for encoder/decoder
- **`ggml/`**: Machine learning library providing tensor operations and hardware backends
- **`examples/`**: Various example applications and utilities
- **`models/`**: Model download scripts and conversion utilities

### Model Architecture

Whisper uses an encoder-decoder transformer architecture:

1. **Encoder**: Processes the audio spectrogram (mel filterbank)
   - 2 convolutional layers for feature extraction
   - N transformer blocks (varies by model size)
   - On Apple Silicon with Core ML, the encoder runs on the Neural Engine
   - With Metal, encoder runs on GPU

2. **Decoder**: Generates text tokens autoregressively
   - Token embedding layer
   - N transformer blocks with self-attention and cross-attention
   - Always runs on CPU (or Metal on Apple Silicon)

3. **Audio Processing**:
   - Input: Raw audio at 16kHz sample rate
   - STFT with 400-point FFT, 160 hop length
   - 80-channel mel filterbank
   - 30-second chunks processed sequentially

### Hardware Backend Selection

On macOS, the library automatically uses available hardware:

1. **Metal** (default on macOS): GPU acceleration for matrix operations
2. **Core ML** (if enabled): Neural Engine acceleration for encoder
3. **Accelerate** (fallback): Apple's BLAS library for CPU
4. **ARM NEON**: SIMD instructions for ARM CPUs

The backend selection is automatic based on build flags and runtime availability.

## Common Examples

### CLI Tool (`examples/cli/`)

The primary command-line interface for transcription. Built as `whisper-cli`.

### Server (`examples/server/`)

HTTP server with OpenAI-compatible API:

```bash
# Start server
./build/bin/whisper-server -m models/ggml-base.en.bin --host 127.0.0.1 --port 8080

# Transcribe via HTTP
curl 127.0.0.1:8080/inference \
  -H "Content-Type: multipart/form-data" \
  -F file="@samples/jfk.wav" \
  -F response_format="json"
```

### Stream (`examples/stream/`)

Real-time transcription from microphone (requires SDL2):

```bash
./build/bin/whisper-stream -m models/ggml-base.en.bin -t 8 --step 500 --length 5000
```

### Bench (`examples/bench/`)

Performance benchmarking:

```bash
./build/bin/whisper-bench -m models/ggml-base.en.bin
```

## Voice Activity Detection (VAD)

VAD can significantly speed up transcription by detecting speech segments:

```bash
# Download VAD model
./models/download-vad-model.sh silero-v5.1.2

# Use with whisper
./build/bin/whisper-cli \
  -m models/ggml-base.en.bin \
  -f samples/jfk.wav \
  --vad \
  -vm models/ggml-silero-v5.1.2.bin
```

## Key Build Outputs

After building, binaries are located in `build/bin/`:

- `whisper-cli` - Main transcription tool
- `whisper-server` - HTTP server
- `whisper-stream` - Real-time streaming (if SDL2 enabled)
- `whisper-bench` - Performance benchmark
- `quantize` - Model quantization tool

## Performance Tips for macOS

1. **Use Core ML on Apple Silicon**: Build with `-DWHISPER_COREML=1` for 3x+ speedup
2. **Enable Metal**: Metal is enabled by default; ensure not disabled with `-DGGML_METAL=OFF`
3. **Use appropriate model size**: 
   - `tiny`/`base` for real-time on older Macs
   - `small`/`medium` for better accuracy on M1/M2/M3
   - `large` for best quality on M2 Pro/Max or M3 Pro/Max
4. **Quantize models**: Use Q5_0 or Q8_0 quantization to reduce memory without significant quality loss
5. **Adjust thread count**: Use `-t 4` or `-t 8` based on your CPU core count

## File Locations

- **Main library**: `src/whisper.cpp`, `include/whisper.h`
- **Examples**: `examples/*/`
- **Tests**: `tests/`
- **Models**: `models/` (models are downloaded, not in repo)
- **Sample audio**: `samples/`
- **Build outputs**: `build/bin/`
- **Model conversion scripts**: `models/*.py`

## Roadmap / Planned Enhancements

- Resilience: More robust error handling (missing codecs, bad inputs, low disk) and retries.
- Pro features: Optional speaker diarization, language auto-detect hints/fallbacks, VAD tuning
