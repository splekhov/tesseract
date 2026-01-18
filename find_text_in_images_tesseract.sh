#!/usr/bin/env bash

# Usage: ./find_text_in_images.sh /path/to/folder "text_pattern"

SEARCH_PATH="$1"
TEXT_PATTERN="$2"

if [[ -z "$SEARCH_PATH" || -z "$TEXT_PATTERN" ]]; then
  echo "Usage: $0 <path> <text_pattern>"
  exit 1
fi

EXTENSIONS="jpg jpeg png gif tiff bmp heic"

echo "Scanning images in: $SEARCH_PATH"
echo "Looking for text: $TEXT_PATTERN"
echo

shopt -s nocaseglob

for ext in $EXTENSIONS; do
  for img in "$SEARCH_PATH"/*.$ext; do
    [[ -e "$img" ]] || continue

    OCR_TEXT=$(tesseract "$img" stdout 2>/dev/null)

    if echo "$OCR_TEXT" | grep -qi "$TEXT_PATTERN"; then
      echo "MATCH: $img"
    fi
  done
done

