#!/bin/bash

# INSTALL_CCify.command
# Comprehensive installer for CCify Video tool
# Installs: Homebrew, ffmpeg, Python 3, mlx-whisper, and sets up CCify Video
# 
# Usage: Double-click this file or run from terminal

set -e  # Exit on error

# ------- Colors -------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

# ------- Helper Functions -------
banner() {
  clear
  echo -e "\n${BOLD}${CYAN}=============================================${NC}"
  echo -e "${BOLD}${CYAN}     CCify Video Installer (macOS)         ${NC}"
  echo -e "${BOLD}${CYAN}=============================================${NC}\n"
}

info()    { echo -e "${CYAN}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[✓]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[!]${NC}    $*"; }
error()   { echo -e "${RED}[✗]${NC}    $*"; }
step()    { echo -e "\n${BOLD}${BLUE}▶ $*${NC}\n"; }

# ------- Verification Functions -------
check_macos() {
  if [[ "$OSTYPE" != "darwin"* ]]; then
    error "This installer is for macOS only."
    error "Detected OS: $OSTYPE"
    exit 1
  fi
  success "Running on macOS"
}

check_architecture() {
  ARCH=$(uname -m)
  info "System architecture: $ARCH"
  if [[ "$ARCH" == "arm64" ]]; then
    success "Apple Silicon (M1/M2/M3) detected - MLX Whisper optimized!"
  elif [[ "$ARCH" == "x86_64" ]]; then
    warn "Intel Mac detected - MLX Whisper may not be available"
    warn "Consider using standard Whisper instead"
  fi
}

# ------- Installation Functions -------
install_homebrew() {
  step "Step 1: Installing Homebrew (Package Manager)"
  
  if command -v brew >/dev/null 2>&1; then
    success "Homebrew already installed at: $(which brew)"
    info "Updating Homebrew..."
    brew update || warn "Homebrew update failed, continuing..."
  else
    info "Homebrew not found. Installing..."
    echo ""
    warn "You may be prompted for your password"
    warn "The installer will download and install Homebrew"
    echo ""
    read -p "Press Enter to continue or Ctrl+C to cancel..."
    
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    
    # Add Homebrew to PATH for current session
    if [[ "$ARCH" == "arm64" ]]; then
      eval "$(/opt/homebrew/bin/brew shellenv)"
    else
      eval "$(/usr/local/bin/brew shellenv)"
    fi
    
    if command -v brew >/dev/null 2>&1; then
      success "Homebrew installed successfully!"
    else
      error "Homebrew installation failed"
      exit 1
    fi
  fi
}

install_ffmpeg() {
  step "Step 2: Installing ffmpeg (Video Processing Tool)"
  
  if command -v ffmpeg >/dev/null 2>&1; then
    success "ffmpeg already installed at: $(which ffmpeg)"
    FFMPEG_VERSION=$(ffmpeg -version 2>/dev/null | head -n1)
    info "$FFMPEG_VERSION"
  else
    info "Installing ffmpeg via Homebrew..."
    info "This may take a few minutes..."
    brew install ffmpeg
    
    if command -v ffmpeg >/dev/null 2>&1; then
      success "ffmpeg installed successfully!"
    else
      error "ffmpeg installation failed"
      exit 1
    fi
  fi
}

install_python() {
  step "Step 3: Checking Python 3"
  
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_VERSION=$(python3 --version)
    success "Python 3 found: $PYTHON_VERSION"
    
    # Check if version is 3.9 or higher
    PYTHON_VER=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    if python3 -c "import sys; exit(0 if sys.version_info >= (3, 9) else 1)"; then
      success "Python version $PYTHON_VER is compatible"
    else
      warn "Python $PYTHON_VER detected - Python 3.9+ recommended"
      info "Installing latest Python via Homebrew..."
      brew install python@3.11 || warn "Could not install newer Python, continuing..."
    fi
  else
    info "Python 3 not found. Installing via Homebrew..."
    brew install python@3.11
    
    if command -v python3 >/dev/null 2>&1; then
      success "Python 3 installed successfully!"
    else
      error "Python 3 installation failed"
      exit 1
    fi
  fi
}

install_mlx_whisper() {
  step "Step 4: Installing mlx-whisper (AI Transcription)"
  
  if python3 -c "import mlx_whisper" 2>/dev/null; then
    success "mlx-whisper already installed"
    MLX_VER=$(python3 -c "import mlx_whisper; print(mlx_whisper.__version__)" 2>/dev/null || echo "unknown")
    info "Version: $MLX_VER"
  else
    info "Installing mlx-whisper and dependencies..."
    info "This will download ~2GB of packages (PyTorch, MLX, etc.)"
    echo ""
    warn "This may take 5-10 minutes depending on your connection"
    echo ""
    read -p "Press Enter to continue..."
    
    # Install with --break-system-packages flag for Homebrew Python
    pip3 install --break-system-packages mlx-whisper
    
    if python3 -c "import mlx_whisper" 2>/dev/null; then
      success "mlx-whisper installed successfully!"
    else
      error "mlx-whisper installation failed"
      error "This is required for CCify Video to work"
      exit 1
    fi
  fi
}

setup_ccify() {
  step "Step 5: Setting up CCify Video"
  
  SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
  
  # Check if CCify_Video.command exists
  if [ -f "$SCRIPT_DIR/CCify_Video.command" ]; then
    success "CCify_Video.command found"
    
    # Make executable
    chmod +x "$SCRIPT_DIR/CCify_Video.command"
    success "Made CCify_Video.command executable"
  else
    error "CCify_Video.command not found in $SCRIPT_DIR"
    error "Please ensure CCify_Video.command is in the same folder as this installer"
    exit 1
  fi
  
  # Check for mlx_transcribe.py
  if [ -f "$SCRIPT_DIR/mlx_transcribe.py" ]; then
    success "mlx_transcribe.py found"
  else
    error "mlx_transcribe.py not found at: $SCRIPT_DIR/mlx_transcribe.py"
    error "Please ensure mlx_transcribe.py is in the same directory"
    exit 1
  fi
  
  # Create Desktop shortcut
  echo ""
  read -p "Create desktop shortcut? (Y/n): " CREATE_SHORTCUT
  if [[ ! "$CREATE_SHORTCUT" =~ ^[Nn]$ ]]; then
    ln -sf "$SCRIPT_DIR/CCify_Video.command" "$HOME/Desktop/CCify Video" 2>/dev/null || true
    if [ -L "$HOME/Desktop/CCify Video" ]; then
      success "Desktop shortcut created: ~/Desktop/CCify Video"
    else
      warn "Could not create desktop shortcut"
    fi
  fi
}

test_installation() {
  step "Step 6: Testing Installation"
  
  echo -e "${BOLD}Checking all components...${NC}\n"
  
  # Test Homebrew
  if command -v brew >/dev/null 2>&1; then
    success "Homebrew: ✓ $(brew --version | head -n1)"
  else
    error "Homebrew: ✗ Not found"
    return 1
  fi
  
  # Test ffmpeg
  if command -v ffmpeg >/dev/null 2>&1; then
    success "ffmpeg: ✓ $(ffmpeg -version 2>/dev/null | head -n1 | awk '{print $3}')"
  else
    error "ffmpeg: ✗ Not found"
    return 1
  fi
  
  # Test Python
  if command -v python3 >/dev/null 2>&1; then
    success "Python 3: ✓ $(python3 --version | awk '{print $2}')"
  else
    error "Python 3: ✗ Not found"
    return 1
  fi
  
  # Test mlx-whisper
  if python3 -c "import mlx_whisper" 2>/dev/null; then
    success "mlx-whisper: ✓ Installed"
  else
    error "mlx-whisper: ✗ Not installed"
    return 1
  fi
  
  # Test CCify script
  SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
  if [ -x "$SCRIPT_DIR/CCify_Video.command" ]; then
    success "CCify Video: ✓ Ready to use"
  else
    error "CCify Video: ✗ Not found or not executable"
    return 1
  fi
  
  echo ""
  success "All components installed successfully! ✓"
  return 0
}

show_completion_message() {
  banner
  echo -e "${BOLD}${GREEN}Installation Complete!${NC}\n"
  
  echo -e "${BOLD}What's installed:${NC}"
  echo "  ✓ Homebrew - Package manager for macOS"
  echo "  ✓ ffmpeg - Video/audio processing"
  echo "  ✓ Python 3 - Programming language"
  echo "  ✓ mlx-whisper - AI transcription engine"
  echo "  ✓ CCify Video - Caption generation tool"
  echo ""
  
  echo -e "${BOLD}How to use:${NC}"
  echo "  1. Double-click 'CCify Video' on your Desktop"
  echo "  2. OR run: CCify_Video.command from this folder"
  echo "  3. Drag and drop a video file when prompted"
  echo "  4. Wait for transcription and caption generation"
  echo ""
  
  echo -e "${BOLD}Tips:${NC}"
  echo "  • First run will download AI models (~150MB-1.5GB)"
  echo "  • Use 'base.en' model for English videos (fastest)"
  echo "  • Output saved to ~/Downloads/CCify/"
  echo "  • Soft subs can be toggled on/off in video players"
  echo ""
  
  SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
  echo -e "${CYAN}Installation location: $SCRIPT_DIR${NC}"
  echo ""
  
  read -p "Press Enter to exit..."
}

show_error_message() {
  echo ""
  error "Installation failed!"
  echo ""
  echo "Common issues:"
  echo "  • No internet connection"
  echo "  • Insufficient permissions (try with administrator account)"
  echo "  • Disk space full (need ~5GB free)"
  echo "  • macOS version too old (need 10.15+)"
  echo ""
  echo "For help, check the error messages above"
  echo ""
  read -p "Press Enter to exit..."
  exit 1
}

# ------- Main Installation Flow -------
main() {
  banner
  
  echo -e "${BOLD}This installer will set up CCify Video and all dependencies:${NC}"
  echo "  • Homebrew (package manager)"
  echo "  • ffmpeg (video processing)"
  echo "  • Python 3 (if not present)"
  echo "  • mlx-whisper (AI transcription)"
  echo ""
  echo -e "${YELLOW}Installation size: ~4-5GB${NC}"
  echo -e "${YELLOW}Time required: 10-20 minutes${NC}"
  echo ""
  
  read -p "Continue with installation? (y/N): " CONFIRM
  if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
    info "Installation cancelled"
    exit 0
  fi
  
  echo ""
  
  # Run checks
  check_macos
  check_architecture
  
  # Install components
  install_homebrew || show_error_message
  install_ffmpeg || show_error_message
  install_python || show_error_message
  install_mlx_whisper || show_error_message
  setup_ccify || show_error_message
  
  # Verify installation
  if test_installation; then
    show_completion_message
  else
    show_error_message
  fi
}

# Run main installation
main "$@"
