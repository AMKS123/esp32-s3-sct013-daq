#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

sudo apt update
sudo apt install -y python3 python3-pip python3-tk python3-venv git

python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r python/requirements.txt

mkdir -p "$HOME/Documents/esp32_s3_daq"
mkdir -p "$HOME/.config/esp32_s3_daq"

echo
echo "Instalacao concluida."
echo "Execute a interface com: ./run_gui.sh"
echo "Porta serial padrao: /dev/ttyACM0"
