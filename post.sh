#!/bin/bash
# post.sh - X(Twitter)に自動投稿するスクリプト
# Usage: ./post.sh "投稿テキスト"

USER='Profile 1'
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TEXT="${1:-}"

if [ -z "$TEXT" ]; then
  echo "Usage: $0 \"投稿テキスト\""
  exit 1
fi

# URLエンコード
ENCODED=$(python3 -c "import urllib.parse; print(urllib.parse.quote('''${TEXT}'''))")
URL="https://twitter.com/intent/tweet?text=${ENCODED}"

open -na "Google Chrome" --args --profile-directory="${USER}" "${URL}"
sleep 3

osascript -e "
tell application \"Google Chrome\"
  execute front window's active tab javascript (read POSIX file \"${SCRIPT_DIR}/postclick.js\")
end tell"
