#!/usr/bin/env bash

set -euo pipefail

if ! command -v pipx >/dev/null 2>&1; then
	echo "pipx is not installed. Installing pipx..."

	if command -v sudo >/dev/null 2>&1; then
		sudo apt update
		sudo apt install -y pipx
        pipx ensurepath
	else
		apt update
		apt install -y pipx
        pipx ensurepath
	fi

	if ! command -v pipx >/dev/null 2>&1; then
		echo "Unable to install pipx. Please install it manually"
		exit 1
	fi
fi

if command -v hatch >/dev/null 2>&1; then
	echo "hatch is already installed."
	exit 0
else
    echo "Installing hatch"
    pipx install hatch
fi

