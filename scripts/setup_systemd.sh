#!/usr/bin/env bash

set -euo pipefail

# Check if systemd service file exists
if [ ! -f "ibef-backend.service" ]; then
    echo "Systemd service file 'ibef-backend.service' not found. Please create it before running this script."
    exit 1
fi 

# Copy the service file to systemd directory
if command -v sudo >/dev/null 2>&1; then
    sudo cp ibef-backend.service /etc/systemd/system/
else
    cp ibef-backend.service /etc/systemd/system/
fi

# Change CHANGE_ME in the service file to the actual path of the IBEF-Backend project
if command -v sudo >/dev/null 2>&1; then
    sudo sed -i "s|<CHANGE_ME>|$(pwd)|g" /etc/systemd/system/ibef-backend.service
else
    sed -i "s|<CHANGE_ME>|$(pwd)|g" /etc/systemd/system/ibef-backend.service
fi

# Reload systemd to recognize the new service
if command -v sudo >/dev/null 2>&1; then
    sudo systemctl daemon-reload
    sudo systemctl enable ibef-backend.service
    sudo systemctl restart ibef-backend.service
else
    systemctl daemon-reload
    systemctl enable ibef-backend.service
    systemctl restart ibef-backend.service
fi
