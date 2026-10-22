#!/usr/bin/env bash
# Startup script for Franka Emika Panda Flask GUI
set -e

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="$(dirname "$SOURCE_DIR")"

echo "=========================================================="
echo "Sourcing environment from: $WORKSPACE_DIR/setup_env.sh"
source "$WORKSPACE_DIR/setup_env.sh"

echo "Starting Franka Panda Flask GUI..."
exec python3 "$SOURCE_DIR/app.py"
