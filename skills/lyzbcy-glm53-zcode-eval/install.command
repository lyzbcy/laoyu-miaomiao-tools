#!/usr/bin/env bash

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if ! command -v python3 >/dev/null 2>&1; then
    printf '未找到 Python 3。请安装 Python 3.9 或更高版本。\n'
    printf 'Python 3 was not found. Install Python 3.9 or newer.\n'
    printf '按回车关闭 / Press Enter to close...'
    read -r _answer
    exit 1
fi

python3 "$SCRIPT_DIR/zcode-instruct.py"
exit_code=$?

printf '\n按回车关闭 / Press Enter to close...'
read -r _answer
exit "$exit_code"
