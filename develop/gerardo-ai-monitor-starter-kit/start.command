#!/bin/zsh
cd -- "$(dirname -- "$0")" || exit 1
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
uv run python scripts/dev.py --open
