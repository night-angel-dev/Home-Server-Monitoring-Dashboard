#!/bin/bash
# Automated setup script for the dashboard

# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install python3 python3-pip screen -y

# Create virtual environment
python3 -m venv dashboard-venv
source dashboard-venv/bin/activate

# Install Python packages
pip install flask psutil

# Create dashboard directory
mkdir -p ~/dashboard
cp dashboard.py ~/dashboard/

echo "Setup complete! Edit dashboard.py to add your RCON password."