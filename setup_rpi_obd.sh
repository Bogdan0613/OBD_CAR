#!/bin/bash
# Raspberry Pi 5 OBD Setup Script for Mazda 3 2008
# Run this script on your Raspberry Pi 5 to set up OBD connectivity

echo "Setting up OBD connectivity for Mazda 3 2008 on Raspberry Pi 5..."

# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y python3-pip bluetooth bluez-tools python3-tk python3-dev

# Install Python OBD library
pip3 install obd

# Enable Bluetooth
sudo systemctl enable bluetooth
sudo systemctl start bluetooth

# Create udev rule for ELM327 Bluetooth adapter (if using USB)
echo 'SUBSYSTEM=="tty", ATTRS{idVendor}=="0403", ATTRS{idProduct}=="6001", MODE="0666"' | sudo tee /etc/udev/rules.d/99-elm327.rules

# Reload udev rules
sudo udevadm control --reload-rules
sudo udevadm trigger

echo "OBD setup complete!"
echo ""
echo "To connect your ELM327 Bluetooth adapter:"
echo "1. Pair your ELM327 device with Raspberry Pi"
echo "2. Find the device address: hcitool scan"
echo "3. Bind to serial port: sudo rfcomm bind /dev/rfcomm0 <MAC_ADDRESS>"
echo "4. Update OBD_PORT in carbrain.py to '/dev/rfcomm0'"
echo ""
echo "For USB ELM327, the device should appear as /dev/ttyUSB0 automatically."