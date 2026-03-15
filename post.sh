#!/bin/bash
# post.sh - X(Twitter)に自動投稿するスクリプト
# Usage: ./post.sh "投稿テキスト" [ChromeProfileName]

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TEXT="${1:-}"
USER="${2:-Profile 1}"

if [ -z "$TEXT" ]; then
  echo "Usage: $0 \"投稿テキスト\" [ChromeProfileName]"
  echo "  ChromeProfileName: Profile 1, Profile 2, ... (default: Profile 1)"
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
