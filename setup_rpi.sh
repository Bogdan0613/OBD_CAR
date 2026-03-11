#!/bin/bash

# Raspberry Pi Setup Script for CarBrain OBD Dashboard
# This script automates the installation and configuration steps.
# Run as: sudo ./setup_rpi.sh

set -e  # Exit on any error

echo "=== CarBrain Raspberry Pi Setup ==="
echo "This will install dependencies and configure the system."
echo "Press Ctrl+C to abort..."
sleep 3

# 1. Update system packages
echo "Step 1: Updating system packages..."
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-dev python3-tk python3-serial bluetooth bluez-tools python3-full
pip3 install --upgrade pip

# 2. Create virtual environment and install Python dependencies
echo "Step 2: Creating virtual environment and installing Python libraries..."
cd "$(dirname "$0")"  # Go to script directory (project root)
python3 -m venv obd_env
source obd_env/bin/activate
pip install --upgrade pip
pip install obd

# 3. Configure Bluetooth/ELM327 (optional, requires user interaction)
echo "Step 3: Bluetooth setup (manual steps required)"
echo "Please pair your ELM327 adapter manually:"
echo "  sudo bluetoothctl"
echo "  Inside bluetoothctl: scan on, trust <MAC>, pair <MAC>, connect <MAC>"
echo "  Then: sudo rfcomm bind /dev/rfcomm0 <MAC>"
echo ""
echo "For USB adapters, they appear as /dev/ttyUSB0 automatically."
echo "Press Enter when done..."
read -r

# 4. Enable serial port permissions
echo "Step 4: Setting up serial permissions..."
sudo tee /etc/udev/rules.d/99-elm327.rules > /dev/null <<'EOF'
SUBSYSTEM=="tty", ATTRS{idVendor}=="0403", ATTRS{idProduct}=="6001", MODE="0666"
EOF
sudo udevadm control --reload-rules && sudo udevadm trigger

# 5. Configure CarBrain
echo "Step 5: Configuring CarBrain..."
# Edit carbrain.py to enable real OBD
sed -i 's/USE_REAL_OBD = False/USE_REAL_OBD = True/' carbrain/carbrain.py
# Set default port (user can change later)
sed -i 's|OBD_PORT = "/dev/ttyUSB0"|OBD_PORT = "/dev/rfcomm0"|' carbrain/carbrain.py

# 6. Test installation
echo "Step 6: Testing installation..."
source obd_env/bin/activate
python -c "import obd; print('OBD library installed successfully')"

# 7. Setup systemd service for autostart
echo "Step 7: Setting up autostart service..."
sudo tee /etc/systemd/system/carbrain.service > /dev/null <<'EOF'
[Unit]
Description=CarBrain OBD dashboard
After=network.target bluetooth.service

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/OBD_CAR
ExecStart=/home/pi/OBD_CAR/obd_env/bin/python /home/pi/OBD_CAR/carbrain/carbrain.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable carbrain.service

echo "=== Setup Complete ==="
echo "To start manually:"
echo "  source obd_env/bin/activate"
echo "  python3 carbrain/carbrain.py"
echo ""
echo "To start service: sudo systemctl start carbrain.service"
echo "To check status: sudo systemctl status carbrain.service"
echo "Reboot to test autostart: sudo reboot"