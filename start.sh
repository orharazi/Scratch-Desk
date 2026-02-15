#!/bin/bash
# Startup script for Scratch-Desk CNC Control System
# Ensures correct working directory for config file loading

# Change to the script's directory
cd /home/orharazi/Scratch-Desk

# Wait a moment for desktop to fully load
sleep 2

# Start the application
/usr/bin/python3 index.py
