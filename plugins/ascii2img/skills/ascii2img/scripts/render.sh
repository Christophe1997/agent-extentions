#!/usr/bin/env bash
# render.sh — convert an ASCII-art diagram file to PNG via svgbob + SVG→PNG converter.
#
# Usage: render.sh [--font-family "Family, fallback, monospace"] <input.bob> [output.png] [zoom]
#
# Exit codes:
#   0   success (prints absolute PNG path on stdout)
#   2   usage error
#   10  svgbob missing (stderr lists install command)
#   11  no SVG→PNG converter found (stderr lists install commands)
#   20  svgbob failed to parse input
#   21  SVG→PNG conversion failed

set -euo pipefail

usage() {
  echo "Usage: $0 [--font-family \"Family, fallback\"] <input.bob> [output.png] [zoom]" >&2
  exit 2
}

font_family=""
positional=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --font-family)
      [[ -n "${2:-}" ]] || { echo "ERROR: --font-family requires a value" >&2; usage; }
      font_family="$2"
      shift 2
      ;;
    --font-family=*)
      font_family="${1#--font-family=}"
      shift
      ;;
    --) shift; positional+=("$@"); break ;;
    -*) echo "ERROR: unknown option: $1" >&2; usage ;;
    *) positional+=("$1"); shift ;;
  esac
done
set -- "${positional[@]}"

[[ $# -ge 1 ]] || usage

input="$1"
[[ -f "$input" ]] || { echo "input file not found: $input" >&2; exit 2; }

zoom="${3:-2}"

if [[ -n "${2:-}" ]]; then
  output="$2"
else
  dir="$(cd "$(dirname "$input")" && pwd)"
  base="$(basename "$input")"
  output="$dir/${base%.*}.png"
fi

os="$(uname -s)"

if ! command -v svgbob >/dev/null 2>&1; then
  {
    echo "ERROR: svgbob not found."
    case "$os" in
      Darwin)  echo "Install: brew install svgbob" ;;
      Linux)   echo "Install: cargo install svgbob_cli   # or use your package manager" ;;
      *)       echo "Install: see https://github.com/ivanceras/svgbob" ;;
    esac
  } >&2
  exit 10
fi

converter=""
if command -v rsvg-convert >/dev/null 2>&1; then
  converter="rsvg-convert"
elif command -v magick >/dev/null 2>&1; then
  converter="magick"
elif command -v convert >/dev/null 2>&1; then
  converter="convert"
fi

if [[ -z "$converter" ]]; then
  {
    echo "ERROR: no SVG→PNG converter found (tried rsvg-convert, magick, convert)."
    case "$os" in
      Darwin)  echo "Install (recommended): brew install librsvg" ;;
      Linux)   echo "Install (recommended): sudo apt-get install librsvg2-bin   # or equivalent" ;;
      *)       echo "Install librsvg from https://wiki.gnome.org/Projects/LibRsvg" ;;
    esac
  } >&2
  exit 11
fi

tmp_svg="$(mktemp -t ascii2img.XXXXXX.svg)"
trap 'rm -f "$tmp_svg"' EXIT

svgbob_args=("$input" -o "$tmp_svg")
[[ -n "$font_family" ]] && svgbob_args+=(--font-family "$font_family")

if ! svgbob "${svgbob_args[@]}" 2>/dev/null; then
  echo "ERROR: svgbob failed to render $input" >&2
  exit 20
fi

case "$converter" in
  rsvg-convert)
    rsvg-convert -z "$zoom" "$tmp_svg" -o "$output" || { echo "ERROR: rsvg-convert failed" >&2; exit 21; }
    ;;
  magick|convert)
    density=$(( 96 * zoom ))
    "$converter" -density "$density" -background white "$tmp_svg" "$output" || { echo "ERROR: $converter failed" >&2; exit 21; }
    ;;
esac

abs_output="$(cd "$(dirname "$output")" && pwd)/$(basename "$output")"
echo "$abs_output"
