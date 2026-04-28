#!/usr/bin/env bash
# Download [globe_history](https://github.com/adsblol/globe_history/releases) split
# archives (.tar.aa, .tar.ab, …) and extract into data/. Requires jq and curl.
#
# Interactive (TTY): pick one or more releases by index and/or calendar date / range.
# Catalog is prod-only (tag contains -planes-readsb-prod-). Non-interactive: latest prod (CI / pipes).
set -euo pipefail

DATA_DIR="${1:-data}"

fetch_all_releases_json() {
  local page=1 n
  local all_file chunk_file merged
  all_file=$(mktemp)
  chunk_file=$(mktemp)
  merged=$(mktemp)
  trap 'rm -f "$all_file" "$chunk_file" "$merged"' RETURN

  echo '[]' > "$all_file"
  while true; do
    curl -sSL "https://api.github.com/repos/adsblol/globe_history/releases?per_page=100&page=${page}" -o "$chunk_file"
    n=$(jq 'length' "$chunk_file")
    if [[ "${n}" -eq 0 ]]; then
      break
    fi
    jq -s 'add' "$all_file" "$chunk_file" > "$merged" && mv "$merged" "$all_file"
    if [[ "${n}" -lt 100 ]]; then
      break
    fi
    page=$((page + 1))
  done
  cat "$all_file"
}

# JSON array of { tag, date, base } newest-first; prod split-tar releases only (-planes-readsb-prod-).
catalog_json() {
  local releases_json="$1"
  echo "$releases_json" | jq '
    [ .[] | select(.draft | not) | select(.prerelease | not)
 | .tag_name as $tag
      | select($tag | test("-planes-readsb-prod-"))
      | ($tag | capture("^v(?<d>[0-9]{4}\\.[0-9]{2}\\.[0-9]{2})") | .d) as $date
      | ([ .assets[] | select(.name | test("\\.tar\\.aa$")) | .name ] | first) as $aa
      | select($aa != null)
      | { tag: $tag, date: $date, base: ($aa | sub("\\.tar\\.aa$"; "")) }
    ]
  '
}

download_one_release() {
  local releases_json="$1"
  local tag="$2"
  local rel
  rel=$(echo "$releases_json" | jq --arg t "$tag" '[.[] | select(.tag_name == $t)][0]')
  if [[ "$(echo "$rel" | jq -r 'type')" == "null" ]]; then
    echo "Release not found: $tag" >&2
    return 1
  fi

  local base parts
  base=$(echo "$rel" | jq -r '[.assets[].name | select(endswith(".tar.aa"))][0] | sub("\\.tar\\.aa$"; "")')
  if [[ -z "$base" || "$base" == "null" ]]; then
    echo "No .tar.aa asset in $tag" >&2
    return 1
  fi

  local parts=() part_line
  while IFS= read -r part_line; do
    [[ -n "$part_line" ]] && parts+=("$part_line")
  done < <(echo "$rel" | jq -r '.assets[] | select(.name | test("\\.tar\\.(aa|ab|ac|ad|ae|af)$")) | .name' | sort -V)
  if [[ ${#parts[@]} -eq 0 ]]; then
    echo "No split .tar.aa/.ab assets in $tag" >&2
    return 1
  fi

  echo "Release: $tag ($base)"
  for part in "${parts[@]}"; do
    local url
    url=$(echo "$rel" | jq -r --arg n "$part" '.assets[] | select(.name == $n) | .browser_download_url')
    echo "Downloading $part..."
    curl -L -# "$url" -o "$part"
  done

  echo "Extracting..."
  mkdir -p "$base"
  cat "${parts[@]}" | tar -xf - -C "$base"
  rm -f "${parts[@]}"

  echo "Done. Extracted to $DATA_DIR/$base"
}

# Args: catalog_json string, max_index, selection string → prints unique tags, one per line.
resolve_selection() {
  local cat="$1"
  local max_idx="$2"
  local input="$3"
  local -a tags=()
  if [[ -z "${input// /}" ]]; then
    input="1"
  fi

  local token
  local IFS=','
  for token in $input; do
    token="${token// /}"
    [[ -z "$token" ]] && continue

    if [[ "$token" =~ ^([0-9]+)-([0-9]+)$ ]]; then
      local a="${BASH_REMATCH[1]}" b="${BASH_REMATCH[2]}"
      if [[ "$a" -gt "$b" ]]; then
        local t="$a"
        a="$b"
        b="$t"
      fi
      local i
      for ((i = a; i <= b; i++)); do
        if [[ "$i" -lt 1 || "$i" -gt "$max_idx" ]]; then
          echo "Index out of range: $i (1–$max_idx)" >&2
          return 1
        fi
        tags+=("$(echo "$cat" | jq -r --argjson n "$((i - 1))" '.[$n].tag')")
      done
    elif [[ "$token" =~ ^[0-9]+$ ]]; then
      local i="$token"
      if [[ "$i" -lt 1 || "$i" -gt "$max_idx" ]]; then
        echo "Index out of range: $i (1–$max_idx)" >&2
        return 1
      fi
      tags+=("$(echo "$cat" | jq -r --argjson n "$((i - 1))" '.[$n].tag')")
    elif [[ "$token" =~ ^([0-9]{4}\.[0-9]{2}\.[0-9]{2})(\.\.|-)([0-9]{4}\.[0-9]{2}\.[0-9]{2})$ ]]; then
      local d0="${BASH_REMATCH[1]}" d1="${BASH_REMATCH[3]}"
      if [[ "$d0" > "$d1" ]]; then
        local s="$d0"
        d0="$d1"
        d1="$s"
      fi
      if ! echo "$cat" | jq -e --arg a "$d0" --arg b "$d1" '[.[] | select(.date >= $a and .date <= $b)] | length > 0' >/dev/null; then
        echo "No releases in catalog for dates $d0 .. $d1" >&2
        return 1
      fi
      local add_line
      while IFS= read -r add_line; do
        [[ -n "$add_line" ]] && tags+=("$add_line")
      done < <(echo "$cat" | jq -r --arg a "$d0" --arg b "$d1" '[.[] | select(.date >= $a and .date <= $b) | .tag] | unique | .[]')
    elif [[ "$token" =~ ^[0-9]{4}\.[0-9]{2}\.[0-9]{2}$ ]]; then
      if ! echo "$cat" | jq -e --arg d "$token" '[.[] | select(.date == $d)] | length > 0' >/dev/null; then
        echo "No releases in catalog for date $token" >&2
        return 1
      fi
      local add_line
      while IFS= read -r add_line; do
        [[ -n "$add_line" ]] && tags+=("$add_line")
      done < <(echo "$cat" | jq -r --arg d "$token" '[.[] | select(.date == $d) | .tag] | unique | .[]')
    else
      echo "Unrecognized selection token: $token (use indices 1,2,3-5 or dates 2026.04.15 or 2026.04.10..2026.04.15)" >&2
      return 1
    fi
  done

  printf '%s\n' "${tags[@]}" | sort -u
}

run_latest_only() {
  local releases_json cat tag
  releases_json=$(fetch_all_releases_json)
  cat=$(catalog_json "$releases_json")
  tag=$(echo "$cat" | jq -r '.[0].tag')
  if [[ -z "$tag" || "$tag" == "null" ]]; then
    echo "No downloadable prod split-tar release found." >&2
    exit 1
  fi
  mkdir -p "$DATA_DIR"
  ( cd "$DATA_DIR" && download_one_release "$releases_json" "$tag" )
}

run_interactive() {
  local releases_json cat max_idx
  echo "Fetching release list..."
  releases_json=$(fetch_all_releases_json)
  cat=$(catalog_json "$releases_json")
  max_idx=$(echo "$cat" | jq 'length')
  if [[ "$max_idx" -eq 0 ]]; then
    echo "No downloadable prod split-tar releases found." >&2
    exit 1
  fi

  echo ""
  echo "Available globe_history releases — prod only (newest first, index · date · tag):"
  echo "$cat" | jq -r 'to_entries[] | "  \(.key+1 | tostring | if length < 3 then " " * (3 - length) + . else . end)  \(.value.date)  \(.value.tag)"'
  echo ""
  echo "Selection:"
  echo "  • Indices: 1,3,5 or range 3-7 (inclusive)"
  echo "  • One calendar day: 2026.04.15 (prod for that day)"
  echo "  • Inclusive date range: 2026.04.10..2026.04.15 or 2026.04.10-2026.04.15"
  echo "  • Combine with commas: 1,2026.04.14,5-7"
  echo "  • Empty = latest only (1)"
  echo ""
  read -r -p "Enter selection: " selection || true

  local -a chosen_tags=()
  local line
  while IFS= read -r line; do
    [[ -n "$line" ]] && chosen_tags+=("$line")
  done < <(resolve_selection "$cat" "$max_idx" "${selection:-}")

  mkdir -p "$DATA_DIR"
  local t
  for t in "${chosen_tags[@]}"; do
    echo ""
    echo "========== $t =========="
    ( cd "$DATA_DIR" && download_one_release "$releases_json" "$t" )
  done

  echo ""
  echo "All selected releases processed under $DATA_DIR"
  echo "Load heatmaps (bulk: all releases under $DATA_DIR):"
  echo "  python process_adsb_data.py $DATA_DIR"
  echo "Or one release:"
  echo "  python process_adsb_data.py $DATA_DIR/<RELEASE_DIR>/heatmap"
}

main() {
  mkdir -p "$DATA_DIR"
  if [[ -t 0 ]]; then
    run_interactive
  else
    echo "Non-interactive stdin: downloading latest prod release only." >&2
    run_latest_only
  fi
}

main
