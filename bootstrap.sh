#!/bin/bash
# =============================================================================
# bootstrap.sh — one-line install of Faber from GitHub, no clone required.
#
#   curl -fsSL https://raw.githubusercontent.com/uhitlei/faber/main/bootstrap.sh | bash
#
# Piping a script from the internet into bash runs code you have not read.
# Read it first if that matters to you:
#   curl -fsSL .../bootstrap.sh -o bootstrap.sh && less bootstrap.sh && bash bootstrap.sh
#
# Everything after `--` is forwarded to the installer verbatim:
#   ... | bash -s -- --yes --interaction gates --owner-name "Ana Silva" --gh on
#
# Env: FABER_REPO (default uhitlei/faber) · FABER_REF (default main)
# Exit: 0 ok · 1 prerequisite/usage · 2 download or write failure
# =============================================================================
set -eu

REPO="${FABER_REPO:-uhitlei/faber}"
REF="${FABER_REF:-main}"

command -v curl >/dev/null 2>&1 || { echo "ERROR: curl is required" >&2; exit 1; }
command -v tar  >/dev/null 2>&1 || { echo "ERROR: tar is required"  >&2; exit 1; }
command -v git  >/dev/null 2>&1 || { echo "ERROR: git is required"  >&2; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "ERROR: python3 is required" >&2; exit 1; }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "→ downloading $REPO@$REF"
curl -fsSL "https://codeload.github.com/$REPO/tar.gz/$REF" \
  | tar -xz -C "$TMP" --strip-components=1 \
  || { echo "ERROR: could not download $REPO@$REF" >&2; exit 2; }

INSTALLER="$TMP/plugins/faber/install.sh"
[ -f "$INSTALLER" ] || { echo "ERROR: payload not found in the archive ($INSTALLER)" >&2; exit 2; }

# The installer is interactive. When this script is itself piped into bash,
# stdin is the pipe, so reattach the terminal when there is one — otherwise the
# installer falls back to defaults and requires --interaction on the command line.
if [ -e /dev/tty ] && [ -r /dev/tty ]; then
  exec bash "$INSTALLER" "$@" < /dev/tty
else
  exec bash "$INSTALLER" "$@"
fi
