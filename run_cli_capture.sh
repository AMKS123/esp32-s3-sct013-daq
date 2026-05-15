#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  echo "Ambiente virtual nao encontrado. Rode primeiro: ./install_raspberry_pi.sh"
  exit 1
fi

. .venv/bin/activate
python3 python/captura_esp32.py "$@"
