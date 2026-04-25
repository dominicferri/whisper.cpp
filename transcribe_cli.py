#!/usr/bin/env python3
"""
Transcribe CLI - Video/Audio to Text with LLM Chunking
-------------------------------------------------------
Transcribes video/audio files from Downloads using whisper.cpp,
outputs text and LLM-ready chunks to a subfolder.

Uses chunking logic from pdf-curl-fisher for LLM ingestion.
"""

import argparse
import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile
from datetime import datetime
from typing import Optional

# Constants
VERSION = "1.0.0"
DOWNLOADS = pathlib.Path.home() / "Downloads"
WHISPER_DIR = pathlib.Path(__file__).parent.resolve()
WHISPER_CLI = WHISPER_DIR / "build" / "bin" / "whisper-cli"
MODELS_DIR = WHISPER_DIR / "models"

# Default model preference order
MODEL_PREFERENCE = [
    "ggml-base.en.bin",
    "ggml-base.bin",
    "ggml-small.en.bin",
    "ggml-small.bin",
    "ggml-medium.en.bin",
    "ggml-medium.bin",
    "ggml-large-v3-turbo.bin",
]

# Supported formats
VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v", ".mpg", ".mpeg"}
AUDIO_EXTS = {".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac", ".wma"}

# LLM chunking presets (chars, ~4 chars = 1 token)
CHUNK_PRESETS = {
    "gemini": {"size": 800000, "overlap": 2000, "desc": "Gemini 3.0 (2M context) - 1-2 very large chunks"},
    "claude": {"size": 400000, "overlap": 1500, "desc": "Claude 4.5 (500K context) - 2-3 large chunks"},
    "gpt5": {"size": 500000, "overlap": 1500, "desc": "GPT-5.2 (1M context) - 1-2 very large chunks"},
    "gpt4": {"size": 32000, "overlap": 300, "desc": "GPT-4 (128K context) - ~5 chunks"},
    "gpt35": {"size": 8000, "overlap": 200, "desc": "GPT-3.5 (16K context) - many small chunks"},
    "local": {"size": 4000, "overlap": 200, "desc": "Local/small models (4K-8K context)"},
}
DEFAULT_PRESET = "gemini"


class Colors:
    """ANSI color codes"""
    if sys.stdout.isatty():
        GREEN = '\033[92m'
        YELLOW = '\033[93m'
        RED = '\033[91m'
        BLUE = '\033[94m'
        CYAN = '\033[96m'
        BOLD = '\033[1m'
        DIM = '\033[2m'
        END = '\033[0m'
    else:
        GREEN = YELLOW = RED = BLUE = CYAN = BOLD = DIM = END = ''


def find_model() -> Optional[pathlib.Path]:
    """Find the best available whisper model."""
    for model_name in MODEL_PREFERENCE:
        model_path = MODELS_DIR / model_name
        if model_path.exists():
            return model_path
    return None


def find_input_file(name: str) -> Optional[pathlib.Path]:
    """Find input file in Downloads folder."""
    # Try exact path first
    path = pathlib.Path(name)
    if path.exists():
        return path
    
    # Try in Downloads
    dl_path = DOWNLOADS / name
    if dl_path.exists():
        return dl_path
    
    # Try glob matching in Downloads
    matches = list(DOWNLOADS.glob(f"*{name}*"))
    video_matches = [m for m in matches if m.suffix.lower() in VIDEO_EXTS | AUDIO_EXTS]
    if video_matches:
        return video_matches[0]
    
    return None


def extract_audio(video_path: pathlib.Path, output_wav: pathlib.Path) -> bool:
    """Extract audio from video file using ffmpeg."""
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        str(output_wav)
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        return result.returncode == 0
    except Exception as e:
        print(f"{Colors.RED}✗ ffmpeg error: {e}{Colors.END}")
        return False


def transcribe(audio_path: pathlib.Path, model_path: pathlib.Path, output_prefix: pathlib.Path) -> Optional[pathlib.Path]:
    """Run whisper-cli transcription."""
    cmd = [
        str(WHISPER_CLI),
        "-m", str(model_path),
        "-f", str(audio_path),
        "-otxt",
        "-of", str(output_prefix),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
        if result.returncode == 0:
            txt_file = pathlib.Path(f"{output_prefix}.txt")
            if txt_file.exists():
                return txt_file
    except Exception as e:
        print(f"{Colors.RED}✗ whisper error: {e}{Colors.END}")
    return None


def chunk_text(text: str, chunk_size: int = 4000, overlap: int = 200) -> list[dict]:
    """Split text into chunks for LLM context windows."""
    if not text:
        return []
    
    chunks = []
    start = 0
    chunk_id = 0
    
    while start < len(text):
        end = start + chunk_size
        
        # Try to break at sentence/paragraph boundary
        if end < len(text):
            para_break = text.rfind("\n\n", start + chunk_size // 2, end)
            if para_break > start:
                end = para_break + 2
            else:
                for punct in [". ", "! ", "? ", ".\n", "!\n", "?\n"]:
                    sent_break = text.rfind(punct, start + chunk_size // 2, end)
                    if sent_break > start:
                        end = sent_break + len(punct)
                        break
        
        chunk_content = text[start:end].strip()
        if chunk_content:
            chunks.append({
                "chunk_id": chunk_id,
                "text": chunk_content,
                "start_char": start,
                "end_char": end,
                "word_count": len(chunk_content.split()),
            })
            chunk_id += 1
        
        start = end - overlap if end < len(text) else len(text)
    
    return chunks


def compute_hash(text: str) -> str:
    """Compute content hash for deduplication."""
    normalized = " ".join(text.split()).lower()
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]


def process_file(input_path: pathlib.Path, output_dir: pathlib.Path, model_path: pathlib.Path, chunk_size: int = 100000, chunk_overlap: int = 500) -> bool:
    """Process a single video/audio file."""
    print(f"\n{Colors.CYAN}{'─' * 60}{Colors.END}")
    print(f"{Colors.BOLD}Processing: {input_path.name}{Colors.END}")
    print(f"{Colors.CYAN}{'─' * 60}{Colors.END}")
    
    # Create output directory structure
    output_dir.mkdir(parents=True, exist_ok=True)
    text_dir = output_dir / "text"
    chunks_dir = output_dir / "chunks"
    text_dir.mkdir(exist_ok=True)
    chunks_dir.mkdir(exist_ok=True)
    
    base_name = input_path.stem
    
    # Step 1: Extract audio if video
    suffix = input_path.suffix.lower()
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        wav_path = pathlib.Path(tmp.name)
    
    if suffix in VIDEO_EXTS:
        print(f"{Colors.BLUE}[1/4]{Colors.END} Extracting audio from video...")
        if not extract_audio(input_path, wav_path):
            print(f"{Colors.RED}✗ Failed to extract audio{Colors.END}")
            wav_path.unlink(missing_ok=True)
            return False
        print(f"{Colors.GREEN}✓ Audio extracted{Colors.END}")
        audio_file = wav_path
        cleanup_audio = True
    elif suffix in AUDIO_EXTS:
        # Convert to WAV if needed
        if suffix != ".wav":
            print(f"{Colors.BLUE}[1/4]{Colors.END} Converting audio format...")
            if not extract_audio(input_path, wav_path):
                print(f"{Colors.RED}✗ Failed to convert audio{Colors.END}")
                wav_path.unlink(missing_ok=True)
                return False
            audio_file = wav_path
            cleanup_audio = True
        else:
            audio_file = input_path
            cleanup_audio = False
        print(f"{Colors.GREEN}✓ Audio ready{Colors.END}")
    else:
        print(f"{Colors.RED}✗ Unsupported format: {suffix}{Colors.END}")
        wav_path.unlink(missing_ok=True)
        return False
    
    # Step 2: Transcribe
    print(f"{Colors.BLUE}[2/4]{Colors.END} Transcribing with whisper (this may take a while)...")
    
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
        tmp_output = pathlib.Path(tmp.name).with_suffix("")
    
    transcript_file = transcribe(audio_file, model_path, tmp_output)
    
    if cleanup_audio:
        wav_path.unlink(missing_ok=True)
    
    if not transcript_file or not transcript_file.exists():
        print(f"{Colors.RED}✗ Transcription failed{Colors.END}")
        return False
    
    transcript_text = transcript_file.read_text(encoding="utf-8", errors="ignore")
    transcript_file.unlink(missing_ok=True)
    
    if not transcript_text.strip():
        print(f"{Colors.RED}✗ Empty transcript{Colors.END}")
        return False
    
    word_count = len(transcript_text.split())
    print(f"{Colors.GREEN}✓ Transcribed: {word_count:,} words{Colors.END}")
    
    # Step 3: Save full text
    print(f"{Colors.BLUE}[3/4]{Colors.END} Saving transcript...")
    full_text_path = text_dir / f"{base_name}.txt"
    full_text_path.write_text(transcript_text, encoding="utf-8")
    print(f"{Colors.GREEN}✓ Saved: {full_text_path.name}{Colors.END}")
    
    # Step 4: Chunk for LLM
    print(f"{Colors.BLUE}[4/4]{Colors.END} Chunking for LLM ingestion...")
    chunks = chunk_text(transcript_text, chunk_size=chunk_size, overlap=chunk_overlap)
    
    chunk_files = []
    for chunk in chunks:
        chunk_file = chunks_dir / f"{base_name}_chunk_{chunk['chunk_id']:03d}.txt"
        chunk_file.write_text(chunk["text"], encoding="utf-8")
        chunk_files.append(chunk_file.name)
    
    print(f"{Colors.GREEN}✓ Created {len(chunks)} chunks{Colors.END}")
    
    # Save manifest
    manifest = {
        "source_file": input_path.name,
        "source_path": str(input_path),
        "processed": datetime.now().isoformat(),
        "word_count": word_count,
        "char_count": len(transcript_text),
        "chunk_count": len(chunks),
        "content_hash": compute_hash(transcript_text),
        "text_file": full_text_path.name,
        "chunk_files": chunk_files,
        "model_used": model_path.name,
    }
    
    manifest_path = output_dir / "manifest.json"
    
    # Append to existing manifest or create new
    if manifest_path.exists():
        try:
            existing = json.loads(manifest_path.read_text())
            if "files" not in existing:
                existing = {"files": [existing]}
            existing["files"].append(manifest)
            existing["updated"] = datetime.now().isoformat()
        except:
            existing = {"files": [manifest], "created": datetime.now().isoformat()}
    else:
        existing = {"files": [manifest], "created": datetime.now().isoformat()}
    
    manifest_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")
    
    print(f"\n{Colors.GREEN}{'═' * 60}{Colors.END}")
    print(f"{Colors.GREEN}✓ Complete!{Colors.END}")
    print(f"  {Colors.DIM}Output:{Colors.END} {output_dir}")
    print(f"  {Colors.DIM}Text:{Colors.END}   {full_text_path.name}")
    print(f"  {Colors.DIM}Chunks:{Colors.END} {len(chunks)} files")
    print(f"{Colors.GREEN}{'═' * 60}{Colors.END}")
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Transcribe video/audio to text with LLM-ready chunking",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s recording.mp4
  %(prog)s "GMT20260119-191735_Recording_1832x982.mp4"
  %(prog)s ~/Downloads/lecture.mp4 -o ~/Documents/transcripts

Output structure:
  ~/Downloads/Transcripts/<filename>/
  ├── text/
  │   └── <filename>.txt       # Full transcript
  ├── chunks/
  │   ├── <filename>_chunk_000.txt
  │   ├── <filename>_chunk_001.txt
  │   └── ...
  └── manifest.json            # Metadata for LLM processing
"""
    )
    parser.add_argument("input", nargs='?', help="Video/audio file (searches in Downloads if not found)")
    parser.add_argument("-o", "--output", help="Output directory (default: ~/Downloads/Transcripts/<filename>)")
    parser.add_argument("-m", "--model", help="Whisper model file (auto-detected by default)")
    parser.add_argument("-p", "--preset", choices=list(CHUNK_PRESETS.keys()), default=DEFAULT_PRESET,
                        help=f"LLM chunk preset (default: {DEFAULT_PRESET})")
    parser.add_argument("--chunk-size", type=int, help="Override chunk size in characters")
    parser.add_argument("--list-presets", action="store_true", help="List available chunk presets")
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    
    args = parser.parse_args()
    
    # List presets if requested
    if args.list_presets:
        print(f"{Colors.BOLD}Available chunk presets:{Colors.END}\n")
        for name, cfg in CHUNK_PRESETS.items():
            marker = "→" if name == DEFAULT_PRESET else " "
            print(f"  {marker} {Colors.CYAN}{name:8}{Colors.END}  {cfg['desc']}")
            print(f"             ~{cfg['size']//4:,} tokens/chunk, {cfg['overlap']//4} token overlap")
        sys.exit(0)
    
    # Check whisper-cli exists
    if not WHISPER_CLI.exists():
        print(f"{Colors.RED}✗ whisper-cli not found at {WHISPER_CLI}{Colors.END}")
        print(f"  Build it with: cd {WHISPER_DIR} && cmake -B build && cmake --build build -j")
        sys.exit(1)
    
    # Find model
    if args.model:
        model_path = pathlib.Path(args.model)
        if not model_path.exists():
            model_path = MODELS_DIR / args.model
    else:
        model_path = find_model()
    
    if not model_path or not model_path.exists():
        print(f"{Colors.RED}✗ No whisper model found{Colors.END}")
        print(f"  Download one with: {WHISPER_DIR}/models/download-ggml-model.sh base.en")
        sys.exit(1)
    
    print(f"{Colors.DIM}Using model: {model_path.name}{Colors.END}")
    
    # Show preset options and prompt for selection if not specified
    if args.preset == DEFAULT_PRESET and not sys.stdin.isatty():
        # Use default if non-interactive
        pass
    elif args.preset == DEFAULT_PRESET:
        print(f"{Colors.BOLD}\nAvailable chunk presets:{Colors.END}\n")
        preset_names = list(CHUNK_PRESETS.keys())
        for i, name in enumerate(preset_names, 1):
            cfg = CHUNK_PRESETS[name]
            marker = "→" if name == DEFAULT_PRESET else " "
            print(f"  {marker} {Colors.CYAN}[{i}]{Colors.END} {name:8}  {cfg['desc']}")
            print(f"       ~{cfg['size']//4:,} tokens/chunk, {cfg['overlap']//4} token overlap\n")
        
        print(f"Select preset [{Colors.GREEN}1{Colors.END}]: ", end="", flush=True)
        try:
            choice = input().strip()
            if choice:
                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(preset_names):
                    args.preset = preset_names[choice_idx]
                else:
                    print(f"{Colors.YELLOW}Invalid choice, using default ({DEFAULT_PRESET}){Colors.END}")
        except (ValueError, EOFError):
            print(f"\nUsing default ({DEFAULT_PRESET})")
    
    # Find input file
    input_path = find_input_file(args.input)
    if not input_path:
        print(f"{Colors.RED}✗ File not found: {args.input}{Colors.END}")
        print(f"  Searched in current directory and {DOWNLOADS}")
        sys.exit(1)
    
    # Set output directory
    if args.output:
        output_dir = pathlib.Path(args.output)
    else:
        output_dir = DOWNLOADS / "Transcripts" / input_path.stem
    
    # Determine chunk settings
    preset = CHUNK_PRESETS[args.preset]
    chunk_size = args.chunk_size if args.chunk_size else preset["size"]
    chunk_overlap = preset["overlap"]
    
    print(f"{Colors.DIM}Chunk preset: {args.preset} ({chunk_size//4:,} tokens/chunk){Colors.END}")
    
    # Process
    success = process_file(input_path, output_dir, model_path, chunk_size, chunk_overlap)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
