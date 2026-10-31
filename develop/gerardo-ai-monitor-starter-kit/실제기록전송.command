#!/bin/zsh
set -e
cd "${0:A:h}"
uv run python scripts/transfer.py
printf '\n전송 결과를 확인한 뒤 창을 닫으세요.\n'
read -k 1
