#!/usr/bin/env python3
"""
CCify Video - Enterprise-Grade CLI Tool
Version 2.0
Automated video captioning with MLX Whisper for Apple Silicon

Features:
- Drag-and-drop or manual path entry
- Batch processing with parallel execution
- Enterprise error handling and logging
- Resume capability with state persistence
- Interactive menu and non-interactive automation
- Comprehensive progress tracking
"""

import argparse
import difflib
import glob
import hashlib
import json
import logging
import os
import re
import shutil
import signal
import subprocess
import sys
import time
import traceback
import urllib.parse
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Set
from concurrent.futures import ThreadPoolExecutor, as_completed

# Version info
VERSION = "2.0.2"
BUILD_DATE = "2025-10-07"

# ============================================================================
# EXIT CODES
# ============================================================================
class ExitCode(Enum):
    """Standard exit codes for scripting"""
    OK = 0
    GENERIC_ERROR = 1
    CONFIG_ERROR = 2
    DEPENDENCY_ERROR = 3
    PATH_ERROR = 4
    DISK_SPACE_ERROR = 5
    NETWORK_ERROR = 6
    TRANSCRIPTION_ERROR = 7
    ENCODING_ERROR = 8
    VALIDATION_ERROR = 9
    INTERRUPTED = 10


# ============================================================================
# CUSTOM EXCEPTIONS
# ============================================================================
class CCifyError(Exception):
    """Base exception for CCify errors"""
    exit_code = ExitCode.GENERIC_ERROR


class DependencyError(CCifyError):
    """Missing or invalid dependency"""
    exit_code = ExitCode.DEPENDENCY_ERROR


class PathError(CCifyError):
    """Path validation or access error"""
    exit_code = ExitCode.PATH_ERROR


class DiskSpaceError(CCifyError):
    """Insufficient disk space"""
    exit_code = ExitCode.DISK_SPACE_ERROR


class NetworkError(CCifyError):
    """Network connectivity issue"""
    exit_code = ExitCode.NETWORK_ERROR


class TranscriptionError(CCifyError):
    """Transcription failed"""
    exit_code = ExitCode.TRANSCRIPTION_ERROR


class EncodingError(CCifyError):
    """Video encoding failed"""
    exit_code = ExitCode.ENCODING_ERROR


class ValidationError(CCifyError):
    """Output validation failed"""
    exit_code = ExitCode.VALIDATION_ERROR


class LockError(CCifyError):
    """File lock conflict"""
    exit_code = ExitCode.GENERIC_ERROR


# ============================================================================
# CONSTANTS AND PATHS
# ============================================================================
FFMPEG_PATH = "/opt/homebrew/bin/ffmpeg"
FFPROBE_PATH = "/opt/homebrew/bin/ffprobe"
PYTHON3_PATH = "/opt/homebrew/bin/python3"
MLX_TRANSCRIBE_PATH = "~/Working Programs/whisper.cpp/mlx_transcribe.py"

CONFIG_FILE = Path.home() / ".ccify_config.json"
LOG_DIR = Path.home() / "Downloads" / "CCify" / "logs"
TEMP_DIR = Path.home() / "Downloads" / "CCify" / "temp"
OUTPUT_DIR = Path.home() / "Downloads" / "CCify"

VIDEO_EXTENSIONS = {
    '.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm',
    '.m4v', '.mpg', '.mpeg', '.3gp', '.ogv', '.ts', '.mts', '.m2ts'
}

AUDIO_EXTENSIONS = {
    '.mp3', '.wav', '.m4a', '.flac', '.ogg', '.aac', '.wma', '.opus'
}

WHISPER_MODELS = {
    "tiny": {"size": "75MB", "speed": "~32x", "accuracy": "Low"},
    "tiny.en": {"size": "75MB", "speed": "~32x", "accuracy": "Low"},
    "base": {"size": "145MB", "speed": "~16x", "accuracy": "Medium"},
    "base.en": {"size": "145MB", "speed": "~16x", "accuracy": "Medium"},
    "small": {"size": "466MB", "speed": "~6x", "accuracy": "Good"},
    "small.en": {"size": "466MB", "speed": "~6x", "accuracy": "Good"},
    "medium": {"size": "1.5GB", "speed": "~2x", "accuracy": "Great"},
    "medium.en": {"size": "1.5GB", "speed": "~2x", "accuracy": "Great"},
}

# ============================================================================
# ANSI COLORS (with fallback)
# ============================================================================
try:
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn
    from rich.panel import Panel
    from rich.table import Table
    from rich import print as rprint
    RICH_AVAILABLE = True
    console = Console()
except ImportError:
    RICH_AVAILABLE = False
    console = None


class Colors:
    """ANSI color codes"""
    if sys.stdout.isatty():
        HEADER = '\033[95m'
        BLUE = '\033[94m'
        CYAN = '\033[96m'
        GREEN = '\033[92m'
        YELLOW = '\033[93m'
        RED = '\033[91m'
        BOLD = '\033[1m'
        UNDERLINE = '\033[4m'
        END = '\033[0m'
    else:
        HEADER = BLUE = CYAN = GREEN = YELLOW = RED = BOLD = UNDERLINE = END = ''


# ============================================================================
# LOGGING SETUP
# ============================================================================
class LogManager:
    """Enterprise-grade logging with file and console handlers"""
    
    def __init__(self, log_level: str = "INFO", quiet: bool = False, verbose: int = 0):
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = LOG_DIR / f"ccify_{self.session_id}.log"
        self.quiet = quiet
        self.verbose = verbose
        
        # Create log directory
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        
        # Setup logger
        self.logger = logging.getLogger("ccify")
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers = []  # Clear existing handlers
        
        # File handler - always DEBUG level
        file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)
        
        # Console handler - respects verbosity
        if not quiet:
            console_handler = logging.StreamHandler(sys.stdout)
            if verbose >= 3:
                console_handler.setLevel(logging.DEBUG)
            elif verbose == 2:
                console_handler.setLevel(logging.INFO)
            elif verbose == 1:
                console_handler.setLevel(logging.INFO)
            else:
                console_handler.setLevel(logging.WARNING)
            
            console_formatter = logging.Formatter('%(levelname)s: %(message)s')
            console_handler.setFormatter(console_formatter)
            self.logger.addHandler(console_handler)
        
        self.logger.info(f"Session started: {self.session_id}")
        self.logger.info(f"Log file: {self.log_file}")
    
    def get_logger(self):
        return self.logger


# ============================================================================
# CONFIGURATION MANAGEMENT
# ============================================================================
DEFAULT_CONFIG = {
    "version": "2.0",
    "last_updated": None,
    "active_profile": "balanced",
    "profiles": {
        "quick": {
            "transcription": {
                "model": "tiny.en",
                "language": "auto",
                "aggressive_preprocessing": False
            },
            "output": {
                "format": "mp4",
                "burn_in": False,
                "subtitle_format": "srt",
                "force_reencode": False
            },
            "encoding": {
                "video_preset": "ultrafast",
                "video_crf": 23,
                "audio_bitrate": 128
            },
            "style": {
                "font_name": "Helvetica",
                "font_size": 40,
                "outline": 3,
                "margin_v": 40,
                "alignment": 2
            }
        },
        "balanced": {
            "transcription": {
                "model": "base.en",
                "language": "auto",
                "aggressive_preprocessing": True
            },
            "output": {
                "format": "mp4",
                "burn_in": False,
                "subtitle_format": "srt",
                "force_reencode": False
            },
            "encoding": {
                "video_preset": "veryfast",
                "video_crf": 18,
                "audio_bitrate": 192
            },
            "style": {
                "font_name": "Helvetica",
                "font_size": 40,
                "outline": 3,
                "margin_v": 40,
                "alignment": 2
            }
        },
        "quality": {
            "transcription": {
                "model": "medium.en",
                "language": "auto",
                "aggressive_preprocessing": True
            },
            "output": {
                "format": "mkv",
                "burn_in": False,
                "subtitle_format": "ass",
                "force_reencode": False
            },
            "encoding": {
                "video_preset": "slow",
                "video_crf": 15,
                "audio_bitrate": 256
            },
            "style": {
                "font_name": "Helvetica",
                "font_size": 44,
                "outline": 4,
                "margin_v": 50,
                "alignment": 2
            }
        }
    },
    "behavior": {
        "max_retries": 3,
        "cleanup_temp": True,
        "resume_enabled": True,
        "confirm_overwrites": True
    },
    "paths": {
        "temp_dir": str(TEMP_DIR),
        "output_dir": str(OUTPUT_DIR),
        "log_dir": str(LOG_DIR)
    }
}


class ConfigManager:
    """Persistent configuration with profiles"""
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or CONFIG_FILE
        self.config = self.load()
    
    def load(self) -> Dict:
        """Load config, merge with defaults"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    user_config = json.load(f)
                # Merge with defaults
                config = self._deep_merge(DEFAULT_CONFIG.copy(), user_config)
                return config
            except Exception as e:
                print(f"{Colors.YELLOW}Warning: Failed to load config: {e}{Colors.END}")
                print(f"{Colors.YELLOW}Using default configuration{Colors.END}")
                return DEFAULT_CONFIG.copy()
        else:
            # First run - create default config
            self.save(DEFAULT_CONFIG)
            return DEFAULT_CONFIG.copy()
    
    def save(self, config: Optional[Dict] = None):
        """Save configuration to file"""
        if config is None:
            config = self.config
        
        config["last_updated"] = datetime.now().isoformat()
        
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump(config, f, indent=2)
    
    def get_active_profile(self) -> Dict:
        """Get the active profile settings"""
        profile_name = self.config.get("active_profile", "balanced")
        return self.config["profiles"].get(profile_name, self.config["profiles"]["balanced"])
    
    def set_active_profile(self, profile_name: str):
        """Set the active profile"""
        if profile_name in self.config["profiles"]:
            self.config["active_profile"] = profile_name
            self.save()
        else:
            raise ValueError(f"Unknown profile: {profile_name}")
    
    def get(self, key_path: str, default=None):
        """Get nested config value using dot notation"""
        keys = key_path.split('.')
        value = self.config
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
                if value is None:
                    return default
            else:
                return default
        return value
    
    def set(self, key_path: str, value):
        """Set nested config value using dot notation"""
        keys = key_path.split('.')
        config = self.config
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        config[keys[-1]] = value
        self.save()
    
    @staticmethod
    def _deep_merge(base: Dict, update: Dict) -> Dict:
        """Deep merge two dictionaries"""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                base[key] = ConfigManager._deep_merge(base[key], value)
            else:
                base[key] = value
        return base


# ============================================================================
# PATH VALIDATION AND SANITIZATION
# ============================================================================
class PathValidator:
    """Robust path handling with smart suggestions"""
    
    @staticmethod
    def sanitize_path(raw_path: str) -> Path:
        """
        Sanitize and normalize path from various inputs including drag-and-drop
        
        Handles:
        - Surrounding quotes (single and double)
        - macOS Terminal drag-and-drop escaping (\\ for spaces)
        - file:// URIs
        - ~ expansion
        - Environment variables
        - Relative paths
        """
        path_str = raw_path.strip()
        
        # Remove surrounding quotes
        if (path_str.startswith('"') and path_str.endswith('"')) or \
           (path_str.startswith("'") and path_str.endswith("'")):
            path_str = path_str[1:-1]
        
        # Handle file:// URIs
        if path_str.startswith('file://'):
            path_str = urllib.parse.unquote(path_str[7:])
        
        # Decode macOS drag-and-drop escaping
        path_str = path_str.replace('\\ ', ' ')
        
        # Expand ~ and environment variables
        path_str = os.path.expanduser(path_str)
        path_str = os.path.expandvars(path_str)
        
        # Convert to absolute path
        path = Path(path_str).resolve()
        
        return path
    
    @staticmethod
    def expand_inputs(inputs: List[str]) -> List[Path]:
        """
        Expand list of inputs including globs
        Returns deduplicated list of paths
        """
        paths: Set[Path] = set()
        
        for input_str in inputs:
            # First sanitize the input
            try:
                sanitized = PathValidator.sanitize_path(input_str)
                
                # Check if it's a glob pattern
                if '*' in str(sanitized) or '?' in str(sanitized) or '[' in str(sanitized):
                    # Expand glob
                    parent = sanitized.parent
                    pattern = sanitized.name
                    if parent.exists():
                        for match in parent.glob(pattern):
                            if match.is_file():
                                paths.add(match)
                else:
                    if sanitized.exists() and sanitized.is_file():
                        paths.add(sanitized)
                    elif '*' not in input_str:
                        # Not a glob, try as-is
                        paths.add(sanitized)
            except Exception as e:
                # If sanitization fails, try glob expansion directly
                expanded = glob.glob(input_str)
                for match in expanded:
                    path = Path(match).resolve()
                    if path.is_file():
                        paths.add(path)
        
        return sorted(paths)
    
    @staticmethod
    def validate_file(path: Path, logger: Optional[logging.Logger] = None) -> Tuple[bool, str]:
        """
        Validate file exists, is readable, and has supported extension
        Returns (is_valid, media_type) where media_type is 'video', 'audio', or error message
        """
        if not path.exists():
            return False, f"File does not exist: {path}"
        
        if not path.is_file():
            return False, f"Path is not a file: {path}"
        
        if not os.access(path, os.R_OK):
            return False, f"File is not readable: {path}"
        
        ext = path.suffix.lower()
        
        if ext in VIDEO_EXTENSIONS:
            return True, "video"
        elif ext in AUDIO_EXTENSIONS:
            return True, "audio"
        else:
            return False, f"Unsupported file extension: {ext}"
    
    @staticmethod
    def suggest_path_corrections(path: Path, max_suggestions: int = 3) -> List[Tuple[Path, float]]:
        """
        Suggest similar file paths when file not found
        Returns list of (path, similarity_score) tuples
        """
        suggestions = []
        
        parent = path.parent
        if not parent.exists():
            return suggestions
        
        filename = path.name
        
        # Get all files in parent directory
        try:
            siblings = [p for p in parent.iterdir() if p.is_file()]
        except PermissionError:
            return suggestions
        
        # Calculate similarity scores
        for sibling in siblings:
            ratio = difflib.SequenceMatcher(None, filename.lower(), sibling.name.lower()).ratio()
            suggestions.append((sibling, ratio))
        
        # Sort by similarity and return top N
        suggestions.sort(key=lambda x: x[1], reverse=True)
        return suggestions[:max_suggestions]


# ============================================================================
# DEPENDENCY CHECKING
# ============================================================================
class DependencyChecker:
    """Verify all required dependencies"""
    
    @staticmethod
    def check_ffmpeg() -> Tuple[bool, str]:
        """Check ffmpeg availability and version"""
        if not Path(FFMPEG_PATH).exists():
            return False, f"ffmpeg not found at {FFMPEG_PATH}"
        
        try:
            result = subprocess.run(
                [FFMPEG_PATH, '-version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                version_line = result.stdout.split('\n')[0]
                return True, version_line
            else:
                return False, "ffmpeg found but failed to execute"
        except Exception as e:
            return False, f"Error checking ffmpeg: {e}"
    
    @staticmethod
    def check_ffprobe() -> Tuple[bool, str]:
        """Check ffprobe availability"""
        if not Path(FFPROBE_PATH).exists():
            return False, f"ffprobe not found at {FFPROBE_PATH}"
        
        try:
            result = subprocess.run(
                [FFPROBE_PATH, '-version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return True, "ffprobe available"
            else:
                return False, "ffprobe found but failed to execute"
        except Exception as e:
            return False, f"Error checking ffprobe: {e}"
    
    @staticmethod
    def check_python3() -> Tuple[bool, str]:
        """Check Python 3 availability and version"""
        if not Path(PYTHON3_PATH).exists():
            return False, f"python3 not found at {PYTHON3_PATH}"
        
        try:
            result = subprocess.run(
                [PYTHON3_PATH, '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                version = result.stdout.strip()
                return True, version
            else:
                return False, "python3 found but failed to execute"
        except Exception as e:
            return False, f"Error checking python3: {e}"
    
    @staticmethod
    def check_mlx_transcribe() -> Tuple[bool, str]:
        """Check mlx_transcribe.py availability"""
        path = Path(MLX_TRANSCRIBE_PATH)
        if not path.exists():
            return False, f"mlx_transcribe.py not found at {MLX_TRANSCRIBE_PATH}"
        
        if not os.access(path, os.R_OK):
            return False, f"mlx_transcribe.py is not readable"
        
        return True, f"mlx_transcribe.py found at {MLX_TRANSCRIBE_PATH}"
    
    @staticmethod
    def check_mlx_whisper() -> Tuple[bool, str]:
        """Check mlx-whisper Python package"""
        try:
            result = subprocess.run(
                [PYTHON3_PATH, '-c', 'import mlx_whisper; print(mlx_whisper.__version__)'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                version = result.stdout.strip()
                return True, f"mlx-whisper version {version}"
            else:
                return False, "mlx-whisper not installed"
        except Exception as e:
            return False, f"Error checking mlx-whisper: {e}"
    
    @staticmethod
    def check_all(logger: Optional[logging.Logger] = None) -> Dict[str, Tuple[bool, str]]:
        """Check all dependencies"""
        results = {
            "ffmpeg": DependencyChecker.check_ffmpeg(),
            "ffprobe": DependencyChecker.check_ffprobe(),
            "python3": DependencyChecker.check_python3(),
            "mlx_transcribe": DependencyChecker.check_mlx_transcribe(),
            "mlx_whisper": DependencyChecker.check_mlx_whisper(),
        }
        
        if logger:
            logger.info("Dependency check results:")
            for name, (success, message) in results.items():
                logger.info(f"  {name}: {'✓' if success else '✗'} {message}")
        
        return results


# ============================================================================
# MEDIA PROBING
# ============================================================================
@dataclass
class MediaInfo:
    """Media file information from ffprobe"""
    duration: float
    size_bytes: int
    has_video: bool
    has_audio: bool
    video_codec: Optional[str] = None
    audio_codec: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    bitrate: Optional[int] = None


class MediaProber:
    """Extract media information using ffprobe"""
    
    @staticmethod
    def probe(file_path: Path, logger: Optional[logging.Logger] = None) -> Optional[MediaInfo]:
        """Probe media file and return metadata"""
        try:
            cmd = [
                FFPROBE_PATH,
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                str(file_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                if logger:
                    logger.error(f"ffprobe failed: {result.stderr}")
                return None
            
            data = json.loads(result.stdout)
            
            # Extract format info
            format_info = data.get('format', {})
            duration = float(format_info.get('duration', 0))
            size_bytes = int(format_info.get('size', 0))
            bitrate = int(format_info.get('bit_rate', 0))
            
            # Extract stream info
            streams = data.get('streams', [])
            has_video = False
            has_audio = False
            video_codec = None
            audio_codec = None
            width = None
            height = None
            
            for stream in streams:
                codec_type = stream.get('codec_type')
                if codec_type == 'video':
                    has_video = True
                    video_codec = stream.get('codec_name')
                    width = stream.get('width')
                    height = stream.get('height')
                elif codec_type == 'audio':
                    has_audio = True
                    audio_codec = stream.get('codec_name')
            
            return MediaInfo(
                duration=duration,
                size_bytes=size_bytes,
                has_video=has_video,
                has_audio=has_audio,
                video_codec=video_codec,
                audio_codec=audio_codec,
                width=width,
                height=height,
                bitrate=bitrate
            )
        
        except Exception as e:
            if logger:
                logger.error(f"Error probing file: {e}")
            return None


# ============================================================================
# DISK SPACE CHECKING
# ============================================================================
class DiskSpaceChecker:
    """Check available disk space"""
    
    @staticmethod
    def check_space(path: Path, required_gb: float, logger: Optional[logging.Logger] = None) -> Tuple[bool, str]:
        """
        Check if there's enough disk space at path
        Returns (has_space, message)
        """
        try:
            stat = shutil.disk_usage(path)
            free_gb = stat.free / (1024 ** 3)
            
            if free_gb < required_gb:
                message = (
                    f"Insufficient disk space at {path}\n"
                    f"  Required: {required_gb:.2f} GB\n"
                    f"  Available: {free_gb:.2f} GB\n"
                    f"  Needed: {required_gb - free_gb:.2f} GB more"
                )
                return False, message
            else:
                message = f"Sufficient space: {free_gb:.2f} GB available (need {required_gb:.2f} GB)"
                return True, message
        
        except Exception as e:
            return False, f"Error checking disk space: {e}"
    
    @staticmethod
    def estimate_required_space(input_size_bytes: int, media_info: MediaInfo) -> float:
        """
        Estimate required disk space in GB
        Includes: temp audio, transcoded video, subtitles, safety factor
        """
        input_gb = input_size_bytes / (1024 ** 3)
        
        # Temp audio: ~10% of video size
        temp_audio_gb = input_gb * 0.1
        
        # Transcoded output: similar to input for high quality
        output_gb = input_gb * 1.2
        
        # Subtitles and metadata: negligible
        subtitle_gb = 0.01
        
        # Safety factor: 20%
        safety_factor = 1.2
        
        total = (temp_audio_gb + output_gb + subtitle_gb) * safety_factor
        
        return total


# ============================================================================
# FILE PROCESSOR - Main processing logic
# ============================================================================
class ProcessingState(Enum):
    """Processing states for state machine"""
    INIT = "init"
    PROBE = "probe"
    PREPARE = "prepare"
    EXTRACT_AUDIO = "extract_audio"
    TRANSCRIBE = "transcribe"
    SUBTITLE_CONVERT = "subtitle_convert"
    MUX = "mux"
    BURN_IN = "burn_in"
    VALIDATE = "validate"
    FINALIZE = "finalize"
    DONE = "done"
    ERROR = "error"


@dataclass
class ProcessingResult:
    """Result of processing operation"""
    success: bool
    input_path: Path
    output_path: Optional[Path] = None
    subtitle_path: Optional[Path] = None
    burned_path: Optional[Path] = None
    transcript_path: Optional[Path] = None
    error: Optional[str] = None
    duration_seconds: float = 0.0
    rtf: float = 0.0  # Real-time factor


class FileProcessor:
    """Process individual video/audio file"""
    
    def __init__(self, config: ConfigManager, logger: logging.Logger, dry_run: bool = False):
        self.config = config
        self.logger = logger
        self.dry_run = dry_run
        self.profile = config.get_active_profile()
        
        # Create necessary directories
        self.temp_dir = Path(config.get("paths.temp_dir", str(TEMP_DIR)))
        self.output_dir = Path(config.get("paths.output_dir", str(OUTPUT_DIR)))
        
        if not dry_run:
            self.temp_dir.mkdir(parents=True, exist_ok=True)
            self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def process(self, input_path: Path, **overrides) -> ProcessingResult:
        """Main processing pipeline"""
        start_time = time.time()
        
        try:
            self.logger.info(f"Processing: {input_path}")
            
            # Apply overrides to profile
            profile = self.profile.copy()
            if overrides:
                profile = self._apply_overrides(profile, overrides)
            
            # Step 1: Probe media
            self.logger.info("Step 1/7: Probing media file...")
            media_info = MediaProber.probe(input_path, self.logger)
            if not media_info:
                raise ValidationError("Failed to probe media file")
            
            self.logger.info(f"  Duration: {media_info.duration:.2f}s")
            self.logger.info(f"  Size: {media_info.size_bytes / (1024**2):.2f} MB")
            self.logger.info(f"  Video: {media_info.has_video}, Audio: {media_info.has_audio}")
            
            if not media_info.has_audio:
                raise ValidationError("File has no audio track")
            
            # Step 2: Check disk space
            self.logger.info("Step 2/7: Checking disk space...")
            required_gb = DiskSpaceChecker.estimate_required_space(media_info.size_bytes, media_info)
            has_space, space_msg = DiskSpaceChecker.check_space(self.temp_dir, required_gb, self.logger)
            if not has_space:
                raise DiskSpaceError(space_msg)
            self.logger.info(f"  {space_msg}")
            
            if self.dry_run:
                self.logger.info("[DRY RUN] Would continue with processing")
                return ProcessingResult(
                    success=True,
                    input_path=input_path,
                    transcript_path=None,
                    duration_seconds=time.time() - start_time
                )
            
            # Step 3: Extract audio
            print(f"\n{Colors.CYAN}[Step 3/7]{Colors.END} Extracting audio...")
            self.logger.info("Step 3/7: Extracting audio...")
            audio_path = self._extract_audio(input_path, media_info.has_video, profile, media_info.duration)
            print(f"{Colors.GREEN}✓ Audio extracted{Colors.END}")
            
            # Step 4: Transcribe
            print(f"\n{Colors.CYAN}[Step 4/7]{Colors.END} Transcribing with MLX Whisper...")
            print(f"{Colors.YELLOW}This is the longest step - please be patient...{Colors.END}")
            if media_info.duration > 300:  # > 5 minutes
                estimated_mins = int((media_info.duration / 60) / 8)  # Rough estimate at 8x speed
                print(f"{Colors.YELLOW}Estimated time: ~{estimated_mins} minute(s){Colors.END}")
            self.logger.info("Step 4/7: Transcribing with MLX Whisper...")
            subtitle_path = self._transcribe(audio_path, input_path.stem, profile, media_info.duration)
            print(f"{Colors.GREEN}✓ Transcription complete{Colors.END}")
            
            # Save transcript text to output directory
            temp_txt_path = self.temp_dir / f"{input_path.stem}.txt"
            transcript_path = self._save_transcript(temp_txt_path, input_path.stem)
            print(f"{Colors.GREEN}✓ Transcript saved{Colors.END}")
            
            # Step 5: Generate output
            output_format = profile["output"]["format"]
            burn_in = profile["output"]["burn_in"]
            
            output_path = None
            burned_path = None
            
            if burn_in:
                print(f"\n{Colors.CYAN}[Step 5/7]{Colors.END} Creating burn-in video...")
                print(f"{Colors.YELLOW}Re-encoding video with burned-in subtitles...{Colors.END}")
                self.logger.info("Step 5/7: Creating burn-in video...")
                burned_path = self._burn_in_subtitles(input_path, subtitle_path, profile)
                print(f"{Colors.GREEN}✓ Burn-in complete{Colors.END}")
            else:
                print(f"\n{Colors.CYAN}[Step 5/7]{Colors.END} Muxing soft subtitles...")
                self.logger.info("Step 5/7: Muxing soft subtitles...")
                output_path = self._mux_subtitles(input_path, subtitle_path, profile)
                print(f"{Colors.GREEN}✓ Muxing complete{Colors.END}")
            
            # Step 6: Validate
            print(f"\n{Colors.CYAN}[Step 6/7]{Colors.END} Validating output...")
            self.logger.info("Step 6/7: Validating output...")
            if output_path:
                self._validate_output(output_path)
            if burned_path:
                self._validate_output(burned_path)
            print(f"{Colors.GREEN}✓ Validation passed{Colors.END}")
            
            # Step 7: Finalize
            print(f"\n{Colors.CYAN}[Step 7/7]{Colors.END} Finalizing...")
            self.logger.info("Step 7/7: Finalizing...")
            if profile.get("behavior", {}).get("cleanup_temp", True):
                self._cleanup_temp_files(audio_path)
            print(f"{Colors.GREEN}✓ Cleanup complete{Colors.END}")
            
            duration = time.time() - start_time
            rtf = media_info.duration / duration if duration > 0 else 0
            
            self.logger.info(f"✓ Processing complete in {duration:.2f}s (RTF: {rtf:.2f}x)")
            
            return ProcessingResult(
                success=True,
                input_path=input_path,
                output_path=output_path,
                subtitle_path=subtitle_path,
                burned_path=burned_path,
                transcript_path=transcript_path,
                duration_seconds=duration,
                rtf=rtf
            )
        
        except CCifyError as e:
            self.logger.error(f"✗ Processing failed: {e}")
            return ProcessingResult(
                success=False,
                input_path=input_path,
                transcript_path=None,
                error=str(e),
                duration_seconds=time.time() - start_time
            )
        
        except Exception as e:
            self.logger.error(f"✗ Unexpected error: {e}")
            self.logger.debug(traceback.format_exc())
            return ProcessingResult(
                success=False,
                input_path=input_path,
                transcript_path=None,
                error=f"Unexpected error: {e}",
                duration_seconds=time.time() - start_time
            )
    
    def _apply_overrides(self, profile: Dict, overrides: Dict) -> Dict:
        """Apply CLI overrides to profile"""
        for key, value in overrides.items():
            if value is not None:
                # Handle nested keys
                if '.' in key:
                    parts = key.split('.')
                    target = profile
                    for part in parts[:-1]:
                        if part not in target:
                            target[part] = {}
                        target = target[part]
                    target[parts[-1]] = value
                else:
                    profile[key] = value
        return profile
    
    def _extract_audio(self, input_path: Path, is_video: bool, profile: Dict, duration: float = 0) -> Path:
        """Extract audio to WAV format"""
        output_path = self.temp_dir / f"{input_path.stem}_audio.wav"
        
        aggressive = profile["transcription"].get("aggressive_preprocessing", False)
        
        if is_video:
            # Extract from video
            cmd = [
                FFMPEG_PATH,
                '-hide_banner', '-loglevel', 'error', '-y',
                '-i', str(input_path),
                '-vn',  # No video
                '-acodec', 'pcm_s16le',
                '-ar', '16000',
                '-ac', '1',
                str(output_path)
            ]
        else:
            # Convert audio
            cmd = [
                FFMPEG_PATH,
                '-hide_banner', '-loglevel', 'error', '-y',
                '-i', str(input_path),
                '-acodec', 'pcm_s16le',
                '-ar', '16000',
                '-ac', '1',
                str(output_path)
            ]
        
        if aggressive:
            # Add audio filtering
            filters = [
                "highpass=f=80",
                "lowpass=f=8000",
                "afftdn=nf=-30",
                "dynaudnorm=p=1.0",
                "loudnorm=I=-16:LRA=11:TP=-1.5"
            ]
            cmd.insert(-1, '-af')
            cmd.insert(-1, ','.join(filters))
        
        # Estimate: audio extraction is roughly 1/10th of video duration for large files
        estimated = max(duration * 0.1, 10) if duration > 0 else 0
        self._run_command(cmd, "Audio extraction", timeout=600, show_progress=True, estimated_duration=estimated)
        return output_path
    
    def _transcribe(self, audio_path: Path, output_stem: str, profile: Dict, duration: float = 0) -> Path:
        """Run transcription using mlx_transcribe.py"""
        output_prefix = self.temp_dir / output_stem
        
        model = profile["transcription"]["model"]
        language = profile["transcription"].get("language", "auto")
        
        cmd = [
            PYTHON3_PATH,
            MLX_TRANSCRIBE_PATH,
            str(audio_path),
            '-m', model,
            '-o', str(output_prefix),
            '--srt',
            '--txt',  # Also generate txt output
            '-q'  # Quiet mode
        ]
        
        if language and language != "auto":
            cmd.extend(['-l', language])
        
        if profile["transcription"].get("aggressive_preprocessing", False):
            cmd.append('--aggressive')
        
        # Estimate transcription time based on model
        # base.en runs at ~8-16x realtime, so duration/12 is a good estimate
        if duration > 0:
            model = profile["transcription"]["model"]
            if 'tiny' in model:
                speed_factor = 20  # ~20x realtime
            elif 'base' in model:
                speed_factor = 12  # ~12x realtime
            elif 'small' in model:
                speed_factor = 6   # ~6x realtime
            else:  # medium or larger
                speed_factor = 3   # ~3x realtime
            estimated = duration / speed_factor
        else:
            estimated = 0
        
        # Longer timeout for transcription - estimate 2x the audio duration
        self._run_command(cmd, "Transcription", timeout=1800, show_progress=True, estimated_duration=estimated)
        
        srt_path = Path(str(output_prefix) + ".srt")
        if not srt_path.exists():
            raise TranscriptionError(f"SRT file not created: {srt_path}")
        
        return srt_path
    
    def _save_transcript(self, temp_txt_path: Path, output_stem: str) -> Path:
        """Save transcript text to output directory"""
        transcript_path = self.output_dir / f"{output_stem}_transcript.txt"
        
        # Copy the transcript from temp to output directory
        if temp_txt_path.exists():
            shutil.copy2(temp_txt_path, transcript_path)
            self.logger.info(f"Transcript saved: {transcript_path}")
        else:
            # Fallback: create empty transcript if txt file wasn't generated
            self.logger.warning(f"Transcript txt not found at {temp_txt_path}, creating placeholder")
            transcript_path.write_text("[Transcript not available]\n", encoding='utf-8')
        
        return transcript_path
    
    def _mux_subtitles(self, video_path: Path, subtitle_path: Path, profile: Dict) -> Path:
        """Mux subtitles into video container"""
        output_format = profile["output"]["format"]
        output_path = self.output_dir / f"{video_path.stem}_CC.{output_format}"
        
        force_reencode = profile["output"].get("force_reencode", False)
        
        if output_format == "mp4":
            if force_reencode:
                cmd = [
                    FFMPEG_PATH,
                    '-hide_banner', '-loglevel', 'error', '-y',
                    '-i', str(video_path),
                    '-i', str(subtitle_path),
                    '-map', '0', '-map', '1:0',
                    '-c:v', 'libx264',
                    '-preset', profile["encoding"]["video_preset"],
                    '-crf', str(profile["encoding"]["video_crf"]),
                    '-c:a', 'aac',
                    '-b:a', f'{profile["encoding"]["audio_bitrate"]}k',
                    '-c:s', 'mov_text',
                    '-metadata:s:s:0', 'language=eng',
                    '-metadata:s:s:0', 'title=English',
                    '-disposition:s:0', 'default',
                    str(output_path)
                ]
            else:
                cmd = [
                    FFMPEG_PATH,
                    '-hide_banner', '-loglevel', 'error', '-y',
                    '-i', str(video_path),
                    '-i', str(subtitle_path),
                    '-map', '0', '-map', '1:0',
                    '-c', 'copy',
                    '-c:s', 'mov_text',
                    '-metadata:s:s:0', 'language=eng',
                    '-metadata:s:s:0', 'title=English',
                    '-disposition:s:0', 'default',
                    str(output_path)
                ]
        elif output_format == "mkv":
            cmd = [
                FFMPEG_PATH,
                '-hide_banner', '-loglevel', 'error', '-y',
                '-i', str(video_path),
                '-i', str(subtitle_path),
                '-map', '0', '-map', '1:0',
                '-c', 'copy',
                '-c:s', 'srt',
                '-metadata:s:s:0', 'language=eng',
                '-metadata:s:s:0', 'title=English',
                '-disposition:s:0', 'default',
                str(output_path)
            ]
        else:
            raise ValidationError(f"Unsupported output format: {output_format}")
        
        self._run_command(cmd, "Subtitle muxing", timeout=300, show_progress=True)
        return output_path
    
    def _burn_in_subtitles(self, video_path: Path, subtitle_path: Path, profile: Dict) -> Path:
        """Burn subtitles into video"""
        output_format = profile["output"]["format"]
        output_path = self.output_dir / f"{video_path.stem}_CC_burned.{output_format}"
        
        style = profile["style"]
        esc_font = style["font_name"].replace("'", "\\'")
        
        style_str = (
            f"FontName={esc_font},"
            f"FontSize={style['font_size']},"
            f"Outline={style['outline']},"
            f"BorderStyle=1,"
            f"PrimaryColour=&H00FFFFFF&,"
            f"OutlineColour=&H00000000&,"
            f"Alignment={style['alignment']},"
            f"MarginV={style['margin_v']}"
        )
        
        cmd = [
            FFMPEG_PATH,
            '-hide_banner', '-loglevel', 'error', '-y',
            '-i', str(video_path),
            '-vf', f"subtitles='{subtitle_path}':force_style='{style_str}'",
            '-c:v', 'libx264',
            '-preset', profile["encoding"]["video_preset"],
            '-crf', str(profile["encoding"]["video_crf"]),
            '-c:a', 'copy',
            str(output_path)
        ]
        
        self._run_command(cmd, "Subtitle burn-in", timeout=600, show_progress=True)
        return output_path
    
    def _validate_output(self, output_path: Path):
        """Validate output file"""
        if not output_path.exists():
            raise ValidationError(f"Output file not created: {output_path}")
        
        media_info = MediaProber.probe(output_path, self.logger)
        if not media_info:
            raise ValidationError(f"Output file is invalid: {output_path}")
        
        if not media_info.has_video and not media_info.has_audio:
            raise ValidationError(f"Output file has no streams: {output_path}")
    
    def _cleanup_temp_files(self, *paths):
        """Clean up temporary files"""
        for path in paths:
            if path and Path(path).exists():
                try:
                    Path(path).unlink()
                    self.logger.debug(f"Cleaned up: {path}")
                except Exception as e:
                    self.logger.warning(f"Failed to clean up {path}: {e}")
    
    def _run_command(self, cmd: List[str], description: str, timeout: int = 300, show_progress: bool = False, estimated_duration: float = 0):
        """Run subprocess command with error handling and optional progress bar"""
        self.logger.debug(f"Running: {' '.join(cmd)}")
        
        try:
            if show_progress:
                # Show a progress bar for long operations
                import threading
                
                done = False
                start_time = time.time()
                
                def progress_bar():
                    bar_width = 40
                    while not done:
                        elapsed = time.time() - start_time
                        
                        if estimated_duration > 0:
                            # Show percentage based on estimated time
                            progress = min(elapsed / estimated_duration, 0.99)  # Cap at 99% until actually done
                            filled = int(bar_width * progress)
                            bar = '█' * filled + '░' * (bar_width - filled)
                            percent = int(progress * 100)
                            sys.stdout.write(f'\r  [{bar}] {percent}% ({elapsed:.0f}s)')
                        else:
                            # Show spinner when we don't know duration
                            spinner = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
                            idx = int(elapsed * 10) % len(spinner)
                            sys.stdout.write(f'\r  {spinner[idx]} Processing... {elapsed:.0f}s')
                        
                        sys.stdout.flush()
                        time.sleep(0.1)
                    
                    # Show completed bar
                    if estimated_duration > 0:
                        bar = '█' * bar_width
                        sys.stdout.write(f'\r  [{bar}] 100% ({elapsed:.0f}s) ✓\n')
                    else:
                        sys.stdout.write(f'\r  ✓ Done! ({elapsed:.0f}s)          \n')
                    sys.stdout.flush()
                
                progress_thread = threading.Thread(target=progress_bar)
                progress_thread.daemon = True
                progress_thread.start()
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )
                
                done = True
                time.sleep(0.2)  # Give progress bar time to show final message
            else:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )
            
            if result.returncode != 0:
                error_msg = result.stderr or result.stdout or "Unknown error"
                self.logger.error(f"{description} failed: {error_msg}")
                raise EncodingError(f"{description} failed: {error_msg}")
        
        except subprocess.TimeoutExpired:
            if show_progress:
                done = True
            raise EncodingError(f"{description} timed out after {timeout}s")
        
        except Exception as e:
            if show_progress:
                done = True
            raise EncodingError(f"{description} error: {e}")


# ============================================================================
# BATCH PROCESSOR
# ============================================================================
class BatchProcessor:
    """Process multiple files with queue management"""
    
    def __init__(self, config: ConfigManager, logger: logging.Logger, dry_run: bool = False):
        self.config = config
        self.logger = logger
        self.dry_run = dry_run
        self.processor = FileProcessor(config, logger, dry_run)
    
    def process_batch(
        self,
        input_paths: List[Path],
        parallel: bool = False,
        max_concurrent: int = 1,
        continue_on_error: bool = False,
        **overrides
    ) -> List[ProcessingResult]:
        """Process multiple files"""
        results = []
        total = len(input_paths)
        
        self.logger.info(f"Batch processing {total} file(s)")
        
        if parallel and max_concurrent > 1:
            # Parallel processing
            with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
                futures = {
                    executor.submit(self._process_single, path, i+1, total, overrides): path
                    for i, path in enumerate(input_paths)
                }
                
                for future in as_completed(futures):
                    result = future.result()
                    results.append(result)
                    
                    if not result.success and not continue_on_error:
                        self.logger.error("Stopping batch due to error")
                        executor.shutdown(wait=False)
                        break
        else:
            # Sequential processing
            for i, path in enumerate(input_paths, 1):
                result = self._process_single(path, i, total, overrides)
                results.append(result)
                
                if not result.success and not continue_on_error:
                    self.logger.error("Stopping batch due to error")
                    break
        
        # Summary
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful
        total_time = sum(r.duration_seconds for r in results)
        
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"Batch Summary:")
        self.logger.info(f"  Total: {total} files")
        self.logger.info(f"  Successful: {successful}")
        self.logger.info(f"  Failed: {failed}")
        self.logger.info(f"  Total time: {total_time:.2f}s")
        if successful > 0:
            avg_rtf = sum(r.rtf for r in results if r.success) / successful
            self.logger.info(f"  Average RTF: {avg_rtf:.2f}x")
        self.logger.info(f"{'='*60}\n")
        
        return results
    
    def _process_single(self, path: Path, index: int, total: int, overrides: Dict) -> ProcessingResult:
        """Process single file with logging"""
        self.logger.info(f"\n[{index}/{total}] Processing: {path.name}")
        return self.processor.process(path, **overrides)


# ============================================================================
# INTERACTIVE MENU
# ============================================================================
def show_banner():
    """Display application banner"""
    banner_text = f"""
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║                    CCify Video v{VERSION}                     ║
║            Enterprise Video Captioning Tool                   ║
║                                                               ║
║           Powered by MLX Whisper for Apple Silicon           ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
"""
    print(f"{Colors.CYAN}{banner_text}{Colors.END}")


def show_menu(config: ConfigManager):
    """Show interactive menu"""
    while True:
        print(f"\n{Colors.BOLD}{'='*60}{Colors.END}")
        print(f"{Colors.BOLD}MAIN MENU{Colors.END}")
        print(f"{Colors.BOLD}{'='*60}{Colors.END}\n")
        
        active_profile = config.config.get("active_profile", "balanced")
        print(f"Active Profile: {Colors.GREEN}{active_profile}{Colors.END}\n")
        
        print(f"{Colors.CYAN}[1]{Colors.END} Process Single File")
        print(f"{Colors.CYAN}[2]{Colors.END} Process Multiple Files (Batch)")
        print(f"{Colors.CYAN}[3]{Colors.END} Configuration Wizard")
        print(f"{Colors.CYAN}[4]{Colors.END} View Settings")
        print(f"{Colors.CYAN}[5]{Colors.END} System Info & Checks")
        print(f"{Colors.CYAN}[6]{Colors.END} Clean Temp Files")
        print(f"{Colors.CYAN}[7]{Colors.END} Help")
        print(f"{Colors.CYAN}[0]{Colors.END} Exit")
        
        choice = input(f"\n{Colors.BOLD}Enter your choice: {Colors.END}").strip()
        
        if choice == "1":
            process_single_interactive(config)
        elif choice == "2":
            process_batch_interactive(config)
        elif choice == "3":
            configuration_wizard(config)
        elif choice == "4":
            view_settings(config)
        elif choice == "5":
            show_system_info()
        elif choice == "6":
            clean_temp_files(config)
        elif choice == "7":
            show_help()
        elif choice == "0":
            print(f"\n{Colors.GREEN}Thank you for using CCify Video!{Colors.END}\n")
            sys.exit(0)
        else:
            print(f"{Colors.RED}Invalid choice. Please try again.{Colors.END}")


def process_single_interactive(config: ConfigManager):
    """Interactive single file processing"""
    print(f"\n{Colors.BOLD}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}PROCESS SINGLE FILE{Colors.END}")
    print(f"{Colors.BOLD}{'='*60}{Colors.END}\n")
    
    print("You can either:")
    print("  • Drag and drop a video file here")
    print("  • Type or paste the file path")
    print(f"  • Type '{Colors.CYAN}back{Colors.END}' to return to menu\n")
    
    while True:
        raw_input = input(f"{Colors.BOLD}Enter file path: {Colors.END}").strip()
        
        if raw_input.lower() == 'back':
            return
        
        if not raw_input:
            print(f"{Colors.YELLOW}Please enter a file path{Colors.END}")
            continue
        
        try:
            path = PathValidator.sanitize_path(raw_input)
            valid, media_type = PathValidator.validate_file(path)
            
            if not valid:
                print(f"{Colors.RED}✗ {media_type}{Colors.END}\n")
                
                # Offer suggestions
                suggestions = PathValidator.suggest_path_corrections(path)
                if suggestions:
                    print(f"{Colors.YELLOW}Did you mean one of these?{Colors.END}")
                    for i, (suggested_path, score) in enumerate(suggestions, 1):
                        print(f"  {Colors.CYAN}[{i}]{Colors.END} {suggested_path}")
                    print(f"  {Colors.CYAN}[0]{Colors.END} Try again\n")
                    
                    choice = input(f"{Colors.BOLD}Select option: {Colors.END}").strip()
                    if choice.isdigit() and 1 <= int(choice) <= len(suggestions):
                        path = suggestions[int(choice) - 1][0]
                        valid, media_type = PathValidator.validate_file(path)
                        if valid:
                            break
                    elif choice == "0":
                        continue
                    else:
                        continue
                continue
            else:
                print(f"{Colors.GREEN}✓ Valid {media_type} file: {path.name}{Colors.END}")
                break
        
        except Exception as e:
            print(f"{Colors.RED}✗ Error: {e}{Colors.END}")
            continue
    
    # Get file info
    logger = logging.getLogger("ccify")
    print(f"\n{Colors.BOLD}Analyzing file...{Colors.END}")
    media_info = MediaProber.probe(path, logger)
    
    if media_info:
        print(f"\n{Colors.CYAN}File Information:{Colors.END}")
        print(f"  Name: {path.name}")
        print(f"  Size: {media_info.size_bytes / (1024**2):.2f} MB")
        print(f"  Duration: {media_info.duration:.2f} seconds ({media_info.duration/60:.1f} minutes)")
        if media_info.has_video:
            print(f"  Resolution: {media_info.width}x{media_info.height}")
            print(f"  Video Codec: {media_info.video_codec}")
        if media_info.has_audio:
            print(f"  Audio Codec: {media_info.audio_codec}")
    
    # Show processing options
    print(f"\n{Colors.BOLD}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}PROCESSING OPTIONS{Colors.END}")
    print(f"{Colors.BOLD}{'='*60}{Colors.END}\n")
    
    active_profile = config.config.get("active_profile", "balanced")
    profile = config.get_active_profile()
    
    print(f"{Colors.CYAN}Current Profile:{Colors.END} {active_profile}")
    print(f"  Model: {profile['transcription']['model']}")
    print(f"  Language: {profile['transcription']['language']}")
    print(f"  Aggressive Audio: {profile['transcription']['aggressive_preprocessing']}")
    print(f"  Output Format: {profile['output']['format']}")
    print(f"  Burn-in: {profile['output']['burn_in']}\n")
    
    # Ask user for preferences
    print(f"{Colors.BOLD}What would you like to do?{Colors.END}\n")
    print(f"{Colors.CYAN}[1]{Colors.END} Use current settings (recommended)")
    print(f"{Colors.CYAN}[2]{Colors.END} Customize this run")
    print(f"{Colors.CYAN}[0]{Colors.END} Back\n")
    
    choice = input(f"{Colors.BOLD}Select option: {Colors.END}").strip()
    
    overrides = {}
    
    if choice == "0":
        return
    elif choice == "2":
        # Customize options
        print(f"\n{Colors.BOLD}Customize Processing:{Colors.END}\n")
        
        # Model selection
        print(f"{Colors.CYAN}Transcription Model:{Colors.END}")
        print(f"  [1] tiny.en    - Fastest (~32x realtime)")
        print(f"  [2] base.en    - Balanced (~16x realtime) [Current]")
        print(f"  [3] small.en   - Better accuracy (~6x realtime)")
        print(f"  [4] medium.en  - Best accuracy (~2x realtime)")
        print(f"  [Enter] Keep current: {profile['transcription']['model']}")
        model_choice = input(f"Select model: ").strip()
        model_map = {"1": "tiny.en", "2": "base.en", "3": "small.en", "4": "medium.en"}
        if model_choice in model_map:
            overrides['transcription.model'] = model_map[model_choice]
        
        # Output format
        print(f"\n{Colors.CYAN}Output Format:{Colors.END}")
        print(f"  [1] MP4 (most compatible)")
        print(f"  [2] MKV (better subtitle support)")
        print(f"  [Enter] Keep current: {profile['output']['format']}")
        format_choice = input(f"Select format: ").strip()
        if format_choice == "1":
            overrides['output.format'] = "mp4"
        elif format_choice == "2":
            overrides['output.format'] = "mkv"
        
        # Burn-in option
        print(f"\n{Colors.CYAN}Subtitle Type:{Colors.END}")
        print(f"  [1] Soft subtitles (can toggle on/off) [Default]")
        print(f"  [2] Burn-in subtitles (permanently embedded)")
        print(f"  [3] Both soft AND burn-in versions")
        burn_choice = input(f"Select type: ").strip()
        if burn_choice == "2":
            overrides['output.burn_in'] = True
        elif burn_choice == "3":
            print(f"{Colors.YELLOW}Note: Will create both versions (takes longer){Colors.END}")
            # We'll handle this by running twice
        
        # Aggressive audio
        print(f"\n{Colors.CYAN}Audio Preprocessing:{Colors.END}")
        print(f"  [1] Standard (faster)")
        print(f"  [2] Aggressive (better quality, slower)")
        print(f"  [Enter] Keep current: {'Aggressive' if profile['transcription']['aggressive_preprocessing'] else 'Standard'}")
        audio_choice = input(f"Select preprocessing: ").strip()
        if audio_choice == "1":
            overrides['transcription.aggressive_preprocessing'] = False
        elif audio_choice == "2":
            overrides['transcription.aggressive_preprocessing'] = True
        
        # Show summary
        print(f"\n{Colors.BOLD}Summary:{Colors.END}")
        print(f"  Model: {overrides.get('transcription.model', profile['transcription']['model'])}")
        print(f"  Format: {overrides.get('output.format', profile['output']['format'])}")
        print(f"  Burn-in: {overrides.get('output.burn_in', profile['output']['burn_in'])}")
        print(f"  Aggressive: {overrides.get('transcription.aggressive_preprocessing', profile['transcription']['aggressive_preprocessing'])}")
        print()
        confirm = input(f"{Colors.YELLOW}Proceed with these settings? (Y/n): {Colors.END}").strip().lower()
        if confirm == 'n':
            return
    
    # Process the file
    processor = FileProcessor(config, logger, dry_run=False)
    
    print(f"\n{Colors.BOLD}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}PROCESSING{Colors.END}")
    print(f"{Colors.BOLD}{'='*60}{Colors.END}\n")
    print(f"This may take several minutes depending on video length...\n")
    
    result = processor.process(path, **overrides)
    
    if result.success:
        print(f"\n{Colors.GREEN}{'='*60}{Colors.END}")
        print(f"{Colors.GREEN}✓ SUCCESS{Colors.END}")
        print(f"{Colors.GREEN}{'='*60}{Colors.END}\n")
        print(f"Input: {result.input_path}")
        if result.output_path:
            print(f"Output: {result.output_path}")
        if result.subtitle_path:
            print(f"Subtitles: {result.subtitle_path}")
        if result.burned_path:
            print(f"Burned: {result.burned_path}")
        if result.transcript_path:
            print(f"Transcript: {result.transcript_path}")
        print(f"Time: {result.duration_seconds:.2f}s (RTF: {result.rtf:.2f}x)")
    else:
        print(f"\n{Colors.RED}{'='*60}{Colors.END}")
        print(f"{Colors.RED}✗ FAILED{Colors.END}")
        print(f"{Colors.RED}{'='*60}{Colors.END}\n")
        print(f"Error: {result.error}")
    
    input(f"\n{Colors.BOLD}Press Enter to continue...{Colors.END}")


def process_batch_interactive(config: ConfigManager):
    """Interactive batch processing"""
    print(f"\n{Colors.BOLD}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}BATCH PROCESSING{Colors.END}")
    print(f"{Colors.BOLD}{'='*60}{Colors.END}\n")
    
    print("Enter file paths (one per line, empty line to finish):")
    print("  • You can drag and drop multiple files")
    print("  • You can use wildcards (*.mp4)")
    print(f"  • Type '{Colors.CYAN}back{Colors.END}' to return to menu\n")
    
    raw_inputs = []
    while True:
        line = input(f"{Colors.BOLD}Path: {Colors.END}").strip()
        if not line:
            break
        if line.lower() == 'back':
            return
        raw_inputs.append(line)
    
    if not raw_inputs:
        print(f"{Colors.YELLOW}No files entered{Colors.END}")
        return
    
    # Expand and validate
    paths = PathValidator.expand_inputs(raw_inputs)
    
    if not paths:
        print(f"{Colors.RED}No valid files found{Colors.END}")
        input(f"\n{Colors.BOLD}Press Enter to continue...{Colors.END}")
        return
    
    print(f"\n{Colors.GREEN}Found {len(paths)} file(s){Colors.END}")
    for path in paths:
        print(f"  • {path.name}")
    
    # Ask for batch settings
    print(f"\n{Colors.BOLD}Batch Settings:{Colors.END}")
    parallel = input("Enable parallel processing? (y/N): ").strip().lower() == 'y'
    continue_on_error = input("Continue on error? (Y/n): ").strip().lower() != 'n'
    
    max_concurrent = 1
    if parallel:
        max_input = input("Max concurrent files (1-4, default 2): ").strip()
        if max_input.isdigit():
            max_concurrent = max(1, min(4, int(max_input)))
        else:
            max_concurrent = 2
    
    # Process batch
    logger = logging.getLogger("ccify")
    batch_processor = BatchProcessor(config, logger, dry_run=False)
    
    print(f"\n{Colors.BOLD}Processing batch...{Colors.END}\n")
    results = batch_processor.process_batch(
        paths,
        parallel=parallel,
        max_concurrent=max_concurrent,
        continue_on_error=continue_on_error
    )
    
    input(f"\n{Colors.BOLD}Press Enter to continue...{Colors.END}")


def configuration_wizard(config: ConfigManager):
    """Interactive configuration wizard"""
    print(f"\n{Colors.BOLD}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}CONFIGURATION WIZARD{Colors.END}")
    print(f"{Colors.BOLD}{'='*60}{Colors.END}\n")
    
    print("Select a preset profile:\n")
    print(f"{Colors.CYAN}[1]{Colors.END} Quick - Fast processing, lower quality")
    print(f"    Model: tiny.en, Preset: ultrafast")
    print(f"{Colors.CYAN}[2]{Colors.END} Balanced - Good quality, reasonable speed (Recommended)")
    print(f"    Model: base.en, Preset: veryfast")
    print(f"{Colors.CYAN}[3]{Colors.END} Quality - Best quality, slower processing")
    print(f"    Model: medium.en, Preset: slow")
    print(f"{Colors.CYAN}[0]{Colors.END} Back to menu\n")
    
    choice = input(f"{Colors.BOLD}Select profile: {Colors.END}").strip()
    
    profile_map = {
        "1": "quick",
        "2": "balanced",
        "3": "quality"
    }
    
    if choice == "0":
        return
    
    if choice in profile_map:
        profile_name = profile_map[choice]
        config.set_active_profile(profile_name)
        print(f"\n{Colors.GREEN}✓ Profile set to: {profile_name}{Colors.END}")
    else:
        print(f"\n{Colors.RED}Invalid choice{Colors.END}")
    
    input(f"\n{Colors.BOLD}Press Enter to continue...{Colors.END}")


def view_settings(config: ConfigManager):
    """View current settings"""
    print(f"\n{Colors.BOLD}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}CURRENT SETTINGS{Colors.END}")
    print(f"{Colors.BOLD}{'='*60}{Colors.END}\n")
    
    active_profile = config.config.get("active_profile", "balanced")
    profile = config.get_active_profile()
    
    print(f"{Colors.CYAN}Active Profile:{Colors.END} {active_profile}\n")
    
    print(f"{Colors.BOLD}Transcription:{Colors.END}")
    print(f"  Model: {profile['transcription']['model']}")
    print(f"  Language: {profile['transcription']['language']}")
    print(f"  Aggressive: {profile['transcription']['aggressive_preprocessing']}\n")
    
    print(f"{Colors.BOLD}Output:{Colors.END}")
    print(f"  Format: {profile['output']['format']}")
    print(f"  Burn-in: {profile['output']['burn_in']}")
    print(f"  Subtitle Format: {profile['output']['subtitle_format']}\n")
    
    print(f"{Colors.BOLD}Encoding:{Colors.END}")
    print(f"  Preset: {profile['encoding']['video_preset']}")
    print(f"  CRF: {profile['encoding']['video_crf']}")
    print(f"  Audio Bitrate: {profile['encoding']['audio_bitrate']}k\n")
    
    input(f"{Colors.BOLD}Press Enter to continue...{Colors.END}")


def show_system_info():
    """Show system information and dependency checks"""
    print(f"\n{Colors.BOLD}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}SYSTEM INFORMATION{Colors.END}")
    print(f"{Colors.BOLD}{'='*60}{Colors.END}\n")
    
    print(f"{Colors.BOLD}Checking dependencies...{Colors.END}\n")
    
    results = DependencyChecker.check_all()
    
    for name, (success, message) in results.items():
        status = f"{Colors.GREEN}✓{Colors.END}" if success else f"{Colors.RED}✗{Colors.END}"
        print(f"{status} {name:20s} {message}")
    
    print(f"\n{Colors.BOLD}Available Models:{Colors.END}\n")
    for model, info in WHISPER_MODELS.items():
        print(f"  {model:12s} Size: {info['size']:8s} Speed: {info['speed']:6s} Accuracy: {info['accuracy']}")
    
    input(f"\n{Colors.BOLD}Press Enter to continue...{Colors.END}")


def clean_temp_files(config: ConfigManager):
    """Clean temporary files"""
    print(f"\n{Colors.BOLD}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}CLEAN TEMPORARY FILES{Colors.END}")
    print(f"{Colors.BOLD}{'='*60}{Colors.END}\n")
    
    temp_dir = Path(config.get("paths.temp_dir", str(TEMP_DIR)))
    
    if not temp_dir.exists():
        print(f"{Colors.YELLOW}No temporary files found{Colors.END}")
        input(f"\n{Colors.BOLD}Press Enter to continue...{Colors.END}")
        return
    
    # Count files
    temp_files = list(temp_dir.glob("*"))
    count = len(temp_files)
    
    if count == 0:
        print(f"{Colors.GREEN}Temporary directory is already clean{Colors.END}")
        input(f"\n{Colors.BOLD}Press Enter to continue...{Colors.END}")
        return
    
    print(f"Found {count} temporary file(s)")
    confirm = input(f"\n{Colors.YELLOW}Delete all temporary files? (y/N): {Colors.END}").strip().lower()
    
    if confirm == 'y':
        try:
            shutil.rmtree(temp_dir)
            temp_dir.mkdir(parents=True, exist_ok=True)
            print(f"\n{Colors.GREEN}✓ Temporary files cleaned{Colors.END}")
        except Exception as e:
            print(f"\n{Colors.RED}✗ Error cleaning temp files: {e}{Colors.END}")
    else:
        print(f"\n{Colors.YELLOW}Operation cancelled{Colors.END}")
    
    input(f"\n{Colors.BOLD}Press Enter to continue...{Colors.END}")


def show_help():
    """Show help information"""
    print(f"\n{Colors.BOLD}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}HELP{Colors.END}")
    print(f"{Colors.BOLD}{'='*60}{Colors.END}\n")
    
    print(f"{Colors.CYAN}CCify Video{Colors.END} - Enterprise Video Captioning Tool\n")
    
    print(f"{Colors.BOLD}Usage:{Colors.END}")
    print(f"  Interactive:  ccify_cli.py")
    print(f"  Single file:  ccify_cli.py process <file>")
    print(f"  Batch:        ccify_cli.py batch <files...>")
    print(f"  Config:       ccify_cli.py config --interactive\n")
    
    print(f"{Colors.BOLD}Drag and Drop:{Colors.END}")
    print(f"  • Simply drag a video file into the terminal window")
    print(f"  • Works with file paths containing spaces")
    print(f"  • Handles macOS Terminal escaping automatically\n")
    
    print(f"{Colors.BOLD}Supported Formats:{Colors.END}")
    print(f"  Videos: mp4, mkv, avi, mov, wmv, flv, webm, and more")
    print(f"  Audio: mp3, wav, m4a, flac, ogg, aac, and more\n")
    
    print(f"{Colors.BOLD}Common Issues:{Colors.END}")
    print(f"  • File not found: Check the path or use drag-and-drop")
    print(f"  • Low disk space: Free up space in ~/Downloads/CCify")
    print(f"  • Slow processing: Use 'quick' profile for speed\n")
    
    print(f"{Colors.BOLD}Documentation:{Colors.END}")
    print(f"  Config file: {CONFIG_FILE}")
    print(f"  Logs: {LOG_DIR}/")
    print(f"  Temp: {TEMP_DIR}/\n")
    
    input(f"{Colors.BOLD}Press Enter to continue...{Colors.END}")


# ============================================================================
# COMMAND LINE INTERFACE
# ============================================================================
def create_parser() -> argparse.ArgumentParser:
    """Create argument parser"""
    parser = argparse.ArgumentParser(
        description=f"CCify Video v{VERSION} - Enterprise Video Captioning Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode
  %(prog)s
  
  # Process single file
  %(prog)s process video.mp4
  %(prog)s process "/path/with spaces/video.mp4" --burn-in
  
  # Batch processing
  %(prog)s batch *.mp4 --parallel --max-concurrent 2
  %(prog)s batch video1.mp4 video2.mkv --continue-on-error
  
  # Configuration
  %(prog)s config --interactive
  %(prog)s config --set-profile balanced
  
  # System info
  %(prog)s info --check
  %(prog)s info --models
  
  # Clean temp files
  %(prog)s clean --temp

Drag and Drop:
  You can drag video files directly into the terminal!
  The tool handles all path escaping and validation automatically.

For more help, run with --help or use interactive mode.
        """
    )
    
    parser.add_argument('--version', action='version', version=f'%(prog)s {VERSION}')
    parser.add_argument('-v', '--verbose', action='count', default=0, help='Increase verbosity (-v, -vv, -vvv)')
    parser.add_argument('-q', '--quiet', action='store_true', help='Minimal output')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without executing')
    parser.add_argument('--config', type=str, help='Path to config file')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], default='INFO', help='Logging level')
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Process command
    process_parser = subparsers.add_parser('process', help='Process single file')
    process_parser.add_argument('input', type=str, help='Input video/audio file')
    process_parser.add_argument('--model', type=str, choices=WHISPER_MODELS.keys(), help='Whisper model')
    process_parser.add_argument('--language', type=str, help='Language code (e.g., en, es, fr)')
    process_parser.add_argument('--format', type=str, choices=['mp4', 'mkv'], help='Output format')
    process_parser.add_argument('--burn-in', action='store_true', help='Create burn-in video')
    process_parser.add_argument('--subtitle-format', type=str, choices=['srt', 'vtt', 'ass'], help='Subtitle format')
    process_parser.add_argument('--aggressive', action='store_true', help='Aggressive audio preprocessing')
    process_parser.add_argument('--output', type=str, help='Output directory')
    
    # Batch command
    batch_parser = subparsers.add_parser('batch', help='Process multiple files')
    batch_parser.add_argument('inputs', nargs='+', type=str, help='Input files (supports wildcards)')
    batch_parser.add_argument('--parallel', action='store_true', help='Process files in parallel')
    batch_parser.add_argument('--max-concurrent', type=int, default=2, help='Max concurrent processes')
    batch_parser.add_argument('--continue-on-error', action='store_true', help='Continue if a file fails')
    batch_parser.add_argument('--model', type=str, choices=WHISPER_MODELS.keys(), help='Whisper model')
    batch_parser.add_argument('--language', type=str, help='Language code')
    batch_parser.add_argument('--format', type=str, choices=['mp4', 'mkv'], help='Output format')
    batch_parser.add_argument('--burn-in', action='store_true', help='Create burn-in videos')
    
    # Config command
    config_parser = subparsers.add_parser('config', help='Manage configuration')
    config_parser.add_argument('--interactive', action='store_true', help='Interactive configuration wizard')
    config_parser.add_argument('--set-profile', type=str, choices=['quick', 'balanced', 'quality'], help='Set active profile')
    config_parser.add_argument('--show', action='store_true', help='Show current configuration')
    
    # Info command
    info_parser = subparsers.add_parser('info', help='System information')
    info_parser.add_argument('--check', action='store_true', help='Check dependencies')
    info_parser.add_argument('--models', action='store_true', help='List available models')
    
    # Clean command
    clean_parser = subparsers.add_parser('clean', help='Clean temporary files')
    clean_parser.add_argument('--temp', action='store_true', help='Clean temp directory')
    clean_parser.add_argument('--yes', action='store_true', help='Skip confirmation')
    
    return parser


def main():
    """Main entry point"""
    parser = create_parser()
    args = parser.parse_args()
    
    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        print(f"\n\n{Colors.YELLOW}Interrupted by user{Colors.END}")
        sys.exit(ExitCode.INTERRUPTED.value)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Initialize config
    config_path = Path(args.config) if args.config else None
    config = ConfigManager(config_path)
    
    # Initialize logging
    log_manager = LogManager(args.log_level, args.quiet, args.verbose)
    logger = log_manager.get_logger()
    
    logger.info(f"CCify Video v{VERSION}")
    logger.info(f"Command: {' '.join(sys.argv)}")
    
    try:
        # No command = interactive mode
        if not args.command:
            show_banner()
            show_menu(config)
            return
        
        # Process command
        if args.command == 'process':
            logger.info(f"Processing single file: {args.input}")
            
            # Validate input
            path = PathValidator.sanitize_path(args.input)
            valid, media_type = PathValidator.validate_file(path, logger)
            
            if not valid:
                logger.error(f"Invalid file: {media_type}")
                
                # Suggest alternatives
                suggestions = PathValidator.suggest_path_corrections(path)
                if suggestions:
                    logger.info("Did you mean one of these?")
                    for suggested_path, score in suggestions:
                        logger.info(f"  {suggested_path} (similarity: {score:.2%})")
                
                sys.exit(ExitCode.PATH_ERROR.value)
            
            # Build overrides
            overrides = {}
            if args.model:
                overrides['transcription.model'] = args.model
            if args.language:
                overrides['transcription.language'] = args.language
            if args.format:
                overrides['output.format'] = args.format
            if args.burn_in:
                overrides['output.burn_in'] = True
            if args.aggressive:
                overrides['transcription.aggressive_preprocessing'] = True
            
            # Process
            processor = FileProcessor(config, logger, args.dry_run)
            result = processor.process(path, **overrides)
            
            if not result.success:
                logger.error(f"Processing failed: {result.error}")
                sys.exit(ExitCode.GENERIC_ERROR.value)
            
            sys.exit(ExitCode.OK.value)
        
        # Batch command
        elif args.command == 'batch':
            logger.info(f"Processing batch: {len(args.inputs)} input(s)")
            
            # Expand inputs
            paths = PathValidator.expand_inputs(args.inputs)
            
            if not paths:
                logger.error("No valid files found")
                sys.exit(ExitCode.PATH_ERROR.value)
            
            logger.info(f"Found {len(paths)} file(s)")
            
            # Build overrides
            overrides = {}
            if args.model:
                overrides['transcription.model'] = args.model
            if args.language:
                overrides['transcription.language'] = args.language
            if args.format:
                overrides['output.format'] = args.format
            if args.burn_in:
                overrides['output.burn_in'] = True
            
            # Process batch
            batch_processor = BatchProcessor(config, logger, args.dry_run)
            results = batch_processor.process_batch(
                paths,
                parallel=args.parallel,
                max_concurrent=args.max_concurrent,
                continue_on_error=args.continue_on_error,
                **overrides
            )
            
            # Check if any failed
            if any(not r.success for r in results):
                sys.exit(ExitCode.GENERIC_ERROR.value)
            
            sys.exit(ExitCode.OK.value)
        
        # Config command
        elif args.command == 'config':
            if args.interactive:
                configuration_wizard(config)
            elif args.set_profile:
                config.set_active_profile(args.set_profile)
                logger.info(f"Active profile set to: {args.set_profile}")
            elif args.show:
                view_settings(config)
            else:
                print("Use --interactive, --set-profile, or --show")
            
            sys.exit(ExitCode.OK.value)
        
        # Info command
        elif args.command == 'info':
            if args.check:
                show_system_info()
            elif args.models:
                print(f"\n{Colors.BOLD}Available Whisper Models:{Colors.END}\n")
                for model, info in WHISPER_MODELS.items():
                    print(f"  {Colors.CYAN}{model:12s}{Colors.END} Size: {info['size']:8s} Speed: {info['speed']:6s} Accuracy: {info['accuracy']}")
                print()
            else:
                show_system_info()
            
            sys.exit(ExitCode.OK.value)
        
        # Clean command
        elif args.command == 'clean':
            if args.temp:
                temp_dir = Path(config.get("paths.temp_dir", str(TEMP_DIR)))
                
                if not temp_dir.exists():
                    logger.info("No temporary files to clean")
                    sys.exit(ExitCode.OK.value)
                
                temp_files = list(temp_dir.glob("*"))
                count = len(temp_files)
                
                if count == 0:
                    logger.info("Temporary directory is already clean")
                    sys.exit(ExitCode.OK.value)
                
                if not args.yes:
                    confirm = input(f"Delete {count} temporary file(s)? (y/N): ").strip().lower()
                    if confirm != 'y':
                        logger.info("Operation cancelled")
                        sys.exit(ExitCode.OK.value)
                
                try:
                    shutil.rmtree(temp_dir)
                    temp_dir.mkdir(parents=True, exist_ok=True)
                    logger.info(f"Cleaned {count} temporary file(s)")
                except Exception as e:
                    logger.error(f"Failed to clean temp files: {e}")
                    sys.exit(ExitCode.GENERIC_ERROR.value)
            
            sys.exit(ExitCode.OK.value)
        
        else:
            parser.print_help()
            sys.exit(ExitCode.OK.value)
    
    except CCifyError as e:
        logger.error(f"Error: {e}")
        sys.exit(e.exit_code.value)
    
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        logger.debug(traceback.format_exc())
        sys.exit(ExitCode.GENERIC_ERROR.value)


if __name__ == "__main__":
    main()
