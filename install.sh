#!/usr/bin/env bash
set -euo pipefail
repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [[ "${1:-}" == '--packages' ]]; then
  shift
  exec bash "$repo_dir/scripts/packages.sh" "$@"
fi
if ! command -v python3 >/dev/null; then
  echo 'Install Python 3 first, or run: ./install.sh --packages' >&2
  exit 1
fi
exec python3 "$repo_dir/scripts/setup.py" "$@"
