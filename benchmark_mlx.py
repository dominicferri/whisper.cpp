#!/usr/bin/env python3
import time
import mlx_whisper

print("=== MLX (mlx-whisper) BENCHMARK ===")

# Warm up
print("Warming up...")
result = mlx_whisper.transcribe("jfk-optimized.wav", path_or_hf_repo="mlx-community/whisper-base.en-mlx")

# Actual benchmark
print("\nRunning benchmark...")
start_time = time.time()
result = mlx_whisper.transcribe("jfk-optimized.wav", path_or_hf_repo="mlx-community/whisper-base.en-mlx")
end_time = time.time()

elapsed = (end_time - start_time) * 1000  # Convert to milliseconds

print(f"\nTranscription: {result['text'].strip()}")
print(f"\nTotal time: {elapsed:.2f} ms")
print(f"Audio duration: 11.0 seconds")
print(f"Speed: {11000/elapsed:.1f}x realtime")
