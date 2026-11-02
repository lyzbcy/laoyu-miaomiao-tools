#!/usr/bin/env bash
# Compatibility entry: all behavior and paths come from the shared runtime.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATE="${1:-$(TZ=Asia/Shanghai date +%F)}"
if [ "$#" -gt 0 ]; then shift; fi
exec python3 "$SCRIPT_DIR/fitness.py" finish --date "$DATE" "$@"
