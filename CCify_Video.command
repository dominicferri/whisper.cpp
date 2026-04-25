#!/bin/bash

# CCify_Video.command
# Launcher for CCify Video - Enterprise-Grade CLI Tool v2.0
#
# This wrapper launches the Python-based CLI tool with full enterprise features:
# - Drag-and-drop or manual path entry
# - Batch processing with parallel execution  
# - Enterprise error handling and logging
# - Interactive menu and non-interactive automation
# - Comprehensive progress tracking

set -euo pipefail

# ------- colors -------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

error()   { echo -e "${RED}[ERROR]${NC} $*"; }
info()    { echo -e "${CYAN}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
CCIFY_CLI="$SCRIPT_DIR/ccify_cli.py"
PYTHON3_PATH="/opt/homebrew/bin/python3"

# ------- pre-flight checks -------
if [ ! -f "$PYTHON3_PATH" ]; then
  error "Python 3 not found at $PYTHON3_PATH"
  error "Please install Python 3 via Homebrew: brew install python3"
  echo ""
  read -p "Press Enter to exit..."
  exit 1
fi

if [ ! -f "$CCIFY_CLI" ]; then
  error "CCify CLI not found at $CCIFY_CLI"
  error "Please ensure ccify_cli.py is in the correct location"
  echo ""
  read -p "Press Enter to exit..."
  exit 1
fi

# ------- launch CCify CLI -------
success "Launching CCify Video CLI..."
echo ""

# Execute the Python CLI with all arguments passed through
exec "$PYTHON3_PATH" "$CCIFY_CLI" "$@"
