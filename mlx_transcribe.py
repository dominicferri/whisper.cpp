#!/usr/bin/env python3
"""
MAX POWER MLX Whisper Transcription Tool
For Audio & Video Files
Optimized for Apple Silicon M-series chips
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

import mlx_whisper

# ANSI colors for epic output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

def print_header(text: str):
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text:^60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.END}\n")

def print_success(text: str):
    print(f"{Colors.GREEN}✓{Colors.END} {text}")

def print_error(text: str):
    print(f"{Colors.RED}✗{Colors.END} {text}")

def print_info(text: str):
    print(f"{Colors.BLUE}ℹ{Colors.END} {text}")

def print_warning(text: str):
    print(f"{Colors.YELLOW}⚠{Colors.END} {text}")

def check_ffmpeg() -> bool:
    """Ensure ffmpeg is available"""
    if shutil.which("ffmpeg") is None:
        print_error("ffmpeg not found. Please install it (e.g., brew install ffmpeg).")
        return False
    return True

def check_disk_space(path: str, min_free_mb: int = 300) -> bool:
    """Check there is at least min_free_mb free space at path"""
    try:
        total, used, free = shutil.disk_usage(path)
        free_mb = free // (1024 * 1024)
        if free_mb < min_free_mb:
            print_warning(f"Low disk space: {free_mb} MB free (< {min_free_mb} MB). Operations may fail.")
            return False
        return True
    except Exception as e:
        print_warning(f"Could not determine disk space: {e}")
        return True

def run_cmd(cmd: List[str], description: str, retries: int = 1, backoff_sec: float = 0.5) -> bool:
    """Run a subprocess with retries and simple backoff"""
    attempt = 0
    while True:
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError as e:
            attempt += 1
            err = e.stderr.decode(errors='ignore') if e.stderr else str(e)
            print_warning(f"{description} failed (attempt {attempt}):\n{err.strip()}")
            if attempt > retries:
                print_error(f"{description} failed after {retries} retries.")
                return False
            time.sleep(backoff_sec * attempt)

# Model configurations - from fastest to most accurate
MODELS = {
    "tiny": "mlx-community/whisper-tiny-mlx",
    "tiny.en": "mlx-community/whisper-tiny.en-mlx",
    "base": "mlx-community/whisper-base-mlx",
    "base.en": "mlx-community/whisper-base.en-mlx",
    "small": "mlx-community/whisper-small-mlx",
    "small.en": "mlx-community/whisper-small.en-mlx",
    "medium": "mlx-community/whisper-medium-mlx",
    "medium.en": "mlx-community/whisper-medium.en-mlx",
}

def is_video_file(filename: str) -> bool:
    """Check if file is a video format"""
    video_extensions = [
        '.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', 
        '.m4v', '.mpg', '.mpeg', '.3gp', '.ogv', '.ts', '.mts'
    ]
    return any(filename.lower().endswith(ext) for ext in video_extensions)

def extract_audio_from_video(video_file: str, output_file: str, channels: int = 1) -> bool:
    """
    Extract audio from video file
    """
    print_info(f"Extracting audio from video: {video_file}")
    
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-i", video_file,
        "-vn",  # No video
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", str(channels),
        output_file
    ]
    
    ok = run_cmd(cmd, "Audio extraction", retries=2, backoff_sec=0.6)
    if ok:
        print_success(f"Audio extracted: {output_file}")
    return ok

def optimize_audio(input_file: str, output_file: str, aggressive: bool = True,
                   vad_enabled: bool = False,
                   vad_threshold_db: float = -40.0,
                   vad_start_silence: float = 0.10,
                   vad_stop_silence: float = 0.10,
                   retries: int = 1) -> bool:
    """
    MAX POWER audio preprocessing with optional VAD (ffmpeg silenceremove)
    """
    print_info(f"Optimizing audio: {input_file}")
    
    if aggressive:
        # AGGRESSIVE mode - maximum quality extraction
        filters = [
            "highpass=f=80",           # Remove deep rumble
            "lowpass=f=8000",          # Speech bandwidth
            "afftdn=nf=-30",           # Strong noise reduction
            "anlmdn=s=10",             # Additional denoise
            "dynaudnorm=p=1.0",        # Aggressive dynamic normalization
            "loudnorm=I=-16:LRA=11:TP=-1.5",  # Loud normalization
        ]
    else:
        # STANDARD mode
        filters = [
            "highpass=f=100",
            "lowpass=f=8000",
            "afftdn=nf=-25",
            "dynaudnorm",
            "loudnorm=I=-18:LRA=7:TP=-2",
        ]
    
    if vad_enabled:
        # Append silenceremove-based VAD
        filters.append(
            f"silenceremove=start_periods=1:start_silence={vad_start_silence}:start_threshold={vad_threshold_db}dB:stop_periods=1:stop_silence={vad_stop_silence}:stop_threshold={vad_threshold_db}dB"
        )
    
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-i", input_file,
        "-af", ",".join(filters),
        "-ar", "16000",
        "-ac", "1",
        "-c:a", "pcm_s16le",
        output_file
    ]
    
    ok = run_cmd(cmd, "Audio optimization", retries=max(1, retries), backoff_sec=0.6)
    if ok:
        print_success(f"Audio optimized: {output_file}")
    return ok

def transcribe_audio(
    audio_file: str,
    model: str = "base.en",
    language: Optional[str] = None,
    verbose: bool = True,
    retries: int = 1,
    language_fallbacks: Optional[List[str]] = None,
) -> Optional[Dict]:
    """
    Transcribe audio using MLX Whisper with optional retries and language fallbacks
    """
    model_path = MODELS.get(model, MODELS["base.en"])
    
    if verbose:
        print_info(f"Model: {model}")
        print_info(f"File: {audio_file}")
    
    attempt = 0
    last_err: Optional[str] = None
    while attempt <= max(0, retries):
        start_time = time.time()
        try:
            result = mlx_whisper.transcribe(
                audio_file,
                path_or_hf_repo=model_path,
                language=language,
                word_timestamps=True,
                verbose=False
            )
            elapsed = time.time() - start_time
            if verbose:
                # Best-effort duration estimate
                duration = len(result.get('segments', [])) * 30
                if not duration:
                    duration = elapsed
                print_success(f"Transcription complete in {elapsed:.2f}s")
                print_info(f"Speed: {duration/elapsed:.1f}x realtime")
            
            text_ok = bool(result.get('text', '').strip())
            # If auto language and result seems empty, try fallbacks
            if (not language) and (not text_ok) and language_fallbacks:
                for lang in language_fallbacks:
                    if verbose:
                        print_warning(f"Retrying with language hint: {lang}")
                    try:
                        result_fb = mlx_whisper.transcribe(
                            audio_file,
                            path_or_hf_repo=model_path,
                            language=lang,
                            word_timestamps=True,
                            verbose=False
                        )
                        if result_fb.get('text', '').strip():
                            return result_fb
                    except Exception as e2:
                        print_warning(f"Language fallback '{lang}' failed: {e2}")
                        continue
            return result
        except Exception as e:
            last_err = str(e)
            attempt += 1
            if attempt > max(0, retries):
                print_error(f"Transcription failed after {retries} retries: {last_err}")
                return None
            print_warning(f"Transcription failed (attempt {attempt}) - retrying ... {last_err}")

def save_txt(text: str, output_file: str):
    """Save plain text transcription"""
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(text.strip() + '\n')
    print_success(f"Saved: {output_file}")

def save_srt(segments: List[Dict], output_file: str):
    """Save SRT subtitle format"""
    with open(output_file, 'w', encoding='utf-8') as f:
        for i, seg in enumerate(segments, 1):
            start = format_timestamp_srt(seg['start'])
            end = format_timestamp_srt(seg['end'])
            text = seg['text'].strip()
            
            f.write(f"{i}\n")
            f.write(f"{start} --> {end}\n")
            f.write(f"{text}\n\n")
    print_success(f"Saved: {output_file}")

def save_vtt(segments: List[Dict], output_file: str):
    """Save WebVTT subtitle format"""
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("WEBVTT\n\n")
        for seg in segments:
            start = format_timestamp_vtt(seg['start'])
            end = format_timestamp_vtt(seg['end'])
            text = seg['text'].strip()
            
            f.write(f"{start} --> {end}\n")
            f.write(f"{text}\n\n")
    print_success(f"Saved: {output_file}")

def save_json(result: Dict, output_file: str):
    """Save full JSON with all metadata"""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print_success(f"Saved: {output_file}")

def format_timestamp_srt(seconds: float) -> str:
    """Format timestamp for SRT (HH:MM:SS,mmm)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

def format_timestamp_vtt(seconds: float) -> str:
    """Format timestamp for VTT (HH:MM:SS.mmm)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"

def split_stereo_to_mono(stereo_file: str, out_left: str, out_right: str, retries: int = 1) -> bool:
    """Split a stereo WAV into two mono WAVs (left/right)"""
    cmd_left = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-i", stereo_file,
        "-af", "pan=mono|c0=c0",
        "-ar", "16000",
        "-ac", "1",
        "-c:a", "pcm_s16le",
        out_left
    ]
    cmd_right = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-i", stereo_file,
        "-af", "pan=mono|c0=c1",
        "-ar", "16000",
        "-ac", "1",
        "-c:a", "pcm_s16le",
        out_right
    ]
    ok_l = run_cmd(cmd_left, "Split left channel", retries=retries, backoff_sec=0.5)
    ok_r = run_cmd(cmd_right, "Split right channel", retries=retries, backoff_sec=0.5)
    return ok_l and ok_r

def perform_diarization_stereo(
    stereo_source_wav: str,
    model: str,
    language: Optional[str],
    language_fallbacks: Optional[List[str]],
    aggressive: bool,
    vad_enabled: bool,
    vad_threshold_db: float,
    vad_start_silence: float,
    vad_stop_silence: float,
    retries: int,
    verbose: bool,
) -> Optional[Dict]:
    """Split stereo into two speakers, transcribe independently, merge by time"""
    base = Path(stereo_source_wav).stem
    left_wav = f"{base}-spkA.wav"
    right_wav = f"{base}-spkB.wav"

    if not split_stereo_to_mono(stereo_source_wav, left_wav, right_wav, retries=max(1, retries)):
        print_warning("Stereo split failed; falling back to single-speaker transcription.")
        return None

    # Optionally optimize each channel
    left_opt = f"{base}-spkA-opt.wav"
    right_opt = f"{base}-spkB-opt.wav"
    if not optimize_audio(left_wav, left_opt, aggressive=aggressive,
                          vad_enabled=vad_enabled,
                          vad_threshold_db=vad_threshold_db,
                          vad_start_silence=vad_start_silence,
                          vad_stop_silence=vad_stop_silence,
                          retries=max(1, retries)):
        return None
    if not optimize_audio(right_wav, right_opt, aggressive=aggressive,
                          vad_enabled=vad_enabled,
                          vad_threshold_db=vad_threshold_db,
                          vad_start_silence=vad_start_silence,
                          vad_stop_silence=vad_stop_silence,
                          retries=max(1, retries)):
        return None

    resA = transcribe_audio(left_opt, model=model, language=language, verbose=verbose,
                            retries=max(1, retries), language_fallbacks=language_fallbacks)
    resB = transcribe_audio(right_opt, model=model, language=language, verbose=verbose,
                            retries=max(1, retries), language_fallbacks=language_fallbacks)
    if not (resA and resB):
        print_warning("One of the speakers failed to transcribe; falling back to single-speaker output.")
        return None

    segs = []
    for s in resA.get('segments', []):
        s2 = dict(s)
        s2['speaker'] = 'SPEAKER A'
        segs.append(s2)
    for s in resB.get('segments', []):
        s2 = dict(s)
        s2['speaker'] = 'SPEAKER B'
        segs.append(s2)

    segs.sort(key=lambda x: x.get('start', 0.0))

    combined_text_lines = []
    for s in segs:
        txt = s.get('text', '').strip()
        spk = s.get('speaker', '')
        if txt:
            combined_text_lines.append(f"[{spk}] {txt}")
    combined_text = "\n".join(combined_text_lines)

    return {"text": combined_text, "segments": segs}

def main():
    parser = argparse.ArgumentParser(
        description='🚀 MAX POWER MLX Whisper Transcription Tool - For Audio & Video - Optimized for Apple Silicon',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Transcribe video file (auto-extracts audio)
  %(prog)s video.mp4 --aggressive --srt
  
  # Quick audio transcription with base model
  %(prog)s audio.mp3
  
  # Use larger model for better accuracy
  %(prog)s video.mov -m medium.en --aggressive
  
  # Create subtitles for video
  %(prog)s movie.mp4 --srt --vtt -o movie_subtitles
  
  # Save all output formats
  %(prog)s podcast.mp3 --all-formats
  
  # Batch process multiple videos
  %(prog)s video1.mp4 video2.mkv video3.mov

Supported formats:
  Videos: mp4, mkv, avi, mov, wmv, flv, webm, m4v, mpg, mpeg, 3gp, ogv
  Audio: mp3, wav, m4a, flac, ogg, aac, wma, opus

Available models (fastest → most accurate):
  tiny, tiny.en, base, base.en, small, small.en, medium, medium.en
        """
    )
    
    parser.add_argument('input_files', nargs='+', help='Input audio or video file(s)')
    parser.add_argument('-m', '--model', default='base.en', choices=MODELS.keys(),
                        help='Whisper model to use (default: base.en)')
    parser.add_argument('-o', '--output', help='Output file prefix (without extension)')
    parser.add_argument('-l', '--language', help='Language code (e.g., en, es, fr). If omitted, auto-detect.')
    parser.add_argument('--language-fallbacks', help='Comma-separated list of languages to try if auto-detect yields poor results (e.g., "en,es,fr")')
    parser.add_argument('--retries', type=int, default=1, help='Retry count for operations (default: 1)')
    parser.add_argument('--no-optimize', action='store_true', 
                        help='Skip audio optimization (use if already optimized)')
    parser.add_argument('--aggressive', action='store_true',
                        help='Use aggressive audio optimization for max quality')
    parser.add_argument('--vad', action='store_true', help='Enable VAD (silence removal) during preprocessing')
    parser.add_argument('--vad-threshold', type=float, default=-40.0, help='VAD threshold in dB (default: -40)')
    parser.add_argument('--vad-start-silence', type=float, default=0.10, help='VAD start silence seconds (default: 0.10)')
    parser.add_argument('--vad-stop-silence', type=float, default=0.10, help='VAD stop silence seconds (default: 0.10)')
    parser.add_argument('--diarize-stereo', action='store_true', help='Split stereo into 2 speakers and merge output')
    parser.add_argument('--txt', action='store_true', help='Save as plain text')
    parser.add_argument('--srt', action='store_true', help='Save as SRT subtitles')
    parser.add_argument('--vtt', action='store_true', help='Save as WebVTT subtitles')
    parser.add_argument('--json', action='store_true', help='Save as JSON with metadata')
    parser.add_argument('--all-formats', action='store_true', 
                        help='Save all output formats (txt, srt, vtt, json)')
    parser.add_argument('-q', '--quiet', action='store_true', help='Minimal output')
    
    args = parser.parse_args()
    
    # If no output format specified, default to txt
    if not (args.txt or args.srt or args.vtt or args.json or args.all_formats):
        args.txt = True
    
    if args.all_formats:
        args.txt = args.srt = args.vtt = args.json = True
    
    if not args.quiet:
        print_header("🚀 MAX POWER MLX WHISPER 🚀")
        print_info(f"Model: {args.model}")
        print_info(f"Files: {len(args.input_files)}")
        if args.aggressive:
            print_warning("AGGRESSIVE MODE ENABLED - Maximum quality extraction")
    
    # Resilience checks
    if not check_ffmpeg():
        sys.exit(1)
    check_disk_space(os.getcwd(), min_free_mb=300)
    
    lang_fallbacks = None
    if args.language_fallbacks:
        lang_fallbacks = [x.strip() for x in args.language_fallbacks.split(',') if x.strip()]
    
    # Process each file
    for input_file in args.input_files:
        if not args.quiet:
            print(f"\n{Colors.BOLD}Processing: {input_file}{Colors.END}")
        
        if not os.path.exists(input_file):
            print_error(f"File not found: {input_file}")
            continue
        
        # Determine output prefix
        if args.output:
            output_prefix = args.output
        else:
            output_prefix = Path(input_file).stem
        
        # Handle video files
        if is_video_file(input_file):
            print_info("📹 Video file detected!")
            # Extract audio from video first (stereo if diarize)
            extracted_audio = f"{output_prefix}-extracted.wav"
            channels = 2 if args.diarize_stereo else 1
            if not extract_audio_from_video(input_file, extracted_audio, channels=channels):
                continue
            
            # Then optimize the extracted audio (if not diarizing stereo, we optimize to mono)
            if args.no_optimize or args.diarize_stereo:
                audio_file = extracted_audio
            else:
                audio_file = f"{output_prefix}-optimized.wav"
                if not optimize_audio(
                    extracted_audio,
                    audio_file,
                    aggressive=args.aggressive,
                    vad_enabled=args.vad,
                    vad_threshold_db=args.vad_threshold,
                    vad_start_silence=args.vad_start_silence,
                    vad_stop_silence=args.vad_stop_silence,
                    retries=max(1, args.retries)
                ):
                    continue
        else:
            # Audio file - process normally
            if args.no_optimize or args.diarize_stereo:
                audio_file = input_file
            else:
                audio_file = f"{output_prefix}-optimized.wav"
                if not optimize_audio(
                    input_file,
                    audio_file,
                    aggressive=args.aggressive,
                    vad_enabled=args.vad,
                    vad_threshold_db=args.vad_threshold,
                    vad_start_silence=args.vad_start_silence,
                    vad_stop_silence=args.vad_stop_silence,
                    retries=max(1, args.retries)
                ):
                    continue
        
        # Transcribe (with optional stereo diarization)
        if args.diarize_stereo:
            # Expect stereo at this point; perform diarization flow
            res_dz = perform_diarization_stereo(
                audio_file,
                model=args.model,
                language=args.language,
                language_fallbacks=lang_fallbacks,
                aggressive=args.aggressive,
                vad_enabled=args.vad,
                vad_threshold_db=args.vad_threshold,
                vad_start_silence=args.vad_start_silence,
                vad_stop_silence=args.vad_stop_silence,
                retries=max(1, args.retries),
                verbose=not args.quiet,
            )
            if res_dz:
                result = res_dz
            else:
                result = transcribe_audio(
                    audio_file,
                    model=args.model,
                    language=args.language,
                    verbose=not args.quiet,
                    retries=max(1, args.retries),
                    language_fallbacks=lang_fallbacks,
                )
        else:
            result = transcribe_audio(
                audio_file,
                model=args.model,
                language=args.language,
                verbose=not args.quiet,
                retries=max(1, args.retries),
                language_fallbacks=lang_fallbacks,
            )
        
        if not result:
            continue
        
        # Save outputs
        if args.txt:
            save_txt(result['text'], f"{output_prefix}.txt")
        
        if args.srt and 'segments' in result:
            save_srt(result['segments'], f"{output_prefix}.srt")
        
        if args.vtt and 'segments' in result:
            save_vtt(result['segments'], f"{output_prefix}.vtt")
        
        if args.json:
            save_json(result, f"{output_prefix}.json")
        
        # Print transcription if not quiet
        if not args.quiet:
            print(f"\n{Colors.BOLD}Transcription:{Colors.END}")
            print(result['text'].strip())
    
    if not args.quiet:
        print_header("✓ ALL COMPLETE ✓")

if __name__ == "__main__":
    main()
