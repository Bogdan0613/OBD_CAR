#!/bin/bash

# Stop and disable old service if it exists
echo "Cleaning up old service..."
sudo systemctl stop carbrain.service 2>/dev/null || true
sudo systemctl disable carbrain.service 2>/dev/null || true
sudo rm -f /etc/systemd/system/carbrain.service

# Reload systemd daemon
sudo systemctl daemon-reload

# Create new service file
echo "Creating new service..."
sudo tee /etc/systemd/system/carbrain.service > /dev/null << 'SERVICEEOF'
[Unit]
Description=CarBrain OBD dashboard
After=network.target bluetooth.service display-manager.service
Wants=display-manager.service

[Service]
Type=simple
User=bohdan
WorkingDirectory=/home/bohdan/OBD_CAR
Environment="DISPLAY=:0"
Environment="XAUTHORITY=/home/bohdan/.Xauthority"
ExecStart=/home/bohdan/OBD_CAR/obd_env/bin/python /home/bohdan/OBD_CAR/carbrain/carbrain.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
SERVICEEOF

# Enable and start service
echo "Enabling and starting service..."
sudo systemctl daemon-reload
sudo systemctl enable carbrain.service
sudo systemctl start carbrain.service

# Show status
echo ""
echo "Service status:"
sudo systemctl status carbrain.service

echo ""
echo "✓ Done! CarBrain will now start automatically on boot."
echo "Check logs with: sudo journalctl -u carbrain.service -f"
