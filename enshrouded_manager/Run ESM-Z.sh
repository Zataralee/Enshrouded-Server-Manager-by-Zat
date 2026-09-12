#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$SCRIPT_DIR/manager.py" ]]; then
  MANAGER="$SCRIPT_DIR/manager.py"
else
  MANAGER="$SCRIPT_DIR/enshrouded_manager/manager.py"
fi
PYTHON="${ESMZ_PYTHON:-python3}"

if ! command -v "$PYTHON" >/dev/null 2>&1; then
  echo "Python 3 was not found. ESM-Z requires Python 3.11 or newer."
  exit 1
fi

if ! "$PYTHON" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)'; then
  echo "ESM-Z requires Python 3.11 or newer."
  "$PYTHON" --version
  exit 1
fi

echo "Starting experimental ESM-Z Linux build..."
echo "Open http://127.0.0.1:8080 after startup."
exec "$PYTHON" "$MANAGER"
