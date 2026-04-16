#!/usr/bin/env bash
# Download latest [globe_history](https://github.com/adsblol/globe_history/releases) release
# (split .tar.aa, .tar.ab ... format) and extract into data/. Requires jq and curl.
set -e
DATA_DIR="${1:-data}"
mkdir -p "$DATA_DIR"
cd "$DATA_DIR"

echo "Fetching latest release..."
RELEASE_JSON=$(curl -sL https://api.github.com/repos/adsblol/globe_history/releases/latest)
TAG=$(echo "$RELEASE_JSON" | jq -r '.tag_name')
# Base name from first .tar.aa asset (e.g. v2026.03.10-planes-readsb-staging-0)
BASE=$(echo "$RELEASE_JSON" | jq -r '[.assets[].name | select(endswith(".tar.aa"))][0] | sub("\\.tar\\.aa$"; "")')
if [ -z "$BASE" ] || [ "$BASE" = "null" ]; then
  echo "No .tar.aa asset found in latest release." >&2
  exit 1
fi

echo "Release: $TAG ($BASE)"
# Sorted list of split parts (.aa, .ab, .ac ...)
PARTS=($(echo "$RELEASE_JSON" | jq -r '.assets[] | select(.name | test("\\.tar\\.(aa|ab|ac|ad|ae|af)$")) | .name' | sort -V))
if [ ${#PARTS[@]} -eq 0 ]; then
  echo "No split .tar.aa/.ab assets found." >&2
  exit 1
fi

for part in "${PARTS[@]}"; do
  url=$(echo "$RELEASE_JSON" | jq -r --arg n "$part" '.assets[] | select(.name == $n) | .browser_download_url')
  echo "Downloading $part..."
  curl -L -# "$url" -o "$part"
done

echo "Extracting..."
mkdir -p "$BASE"
cat "${PARTS[@]}" | tar -xf - -C "$BASE"
rm -f "${PARTS[@]}"

echo "Done. Extracted to $DATA_DIR/$BASE"
echo "Run the loader on the heatmap subfolder:"
echo "  python process_adsb_data.py $DATA_DIR/$BASE/heatmap"
echo "  (or Docker: ... run --rm data-loading /data/$BASE/heatmap)"
