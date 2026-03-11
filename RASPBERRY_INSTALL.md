# Raspberry Pi 5 Deployment Guide

This document explains how to prepare a Raspberry Pi 5 for the CarBrain
application and how to launch the app automatically when the board powers on.

---

## 1. Prepare the Pi

1. **Flash OS**
   - Download Raspberry Pi OS (32‑bit or 64‑bit, Desktop if you need GUI).
   - Use `raspi-imager` or `balenaEtcher` to write the image to an SD card.
   - Boot the Pi, complete first‑time setup (keyboard, network, locale).

2. **Update system packages**
   ```bash
   sudo apt update && sudo apt upgrade -y
   sudo apt install -y python3-pip python3-tk python3-dev bluetooth bluez-tools
   ```

3. **Clone project & install Python libs**
   ```bash
   cd ~
   git clone <your-repo-url> OBD_CAR
   cd OBD_CAR
   pip3 install obd
   ```

4. **Touchscreen configuration** (if using 3.5" display)
   - Follow the vendor’s instructions to enable the framebuffer or X driver.
   - Ensure `/boot/config.txt` has correct `dtparam=spi=on` and display settings.

5. **Bluetooth / ELM327 setup**
   - Power on the ELM327 adapter and pair it:
     ```bash
     sudo bluetoothctl
     # inside bluetoothctl: scan on, trust <MAC>, pair <MAC>, connect <MAC>
     sudo rfcomm bind /dev/rfcomm0 <MAC>
     ```
   - For USB adapters the device appears as `/dev/ttyUSB0` automatically.

6. **Enable serial port permissions**
   ```bash
   echo 'SUBSYSTEM=="tty", ATTRS{idVendor}=="0403", ATTRS{idProduct}=="6001", MODE="0666"' | sudo tee /etc/udev/rules.d/99-elm327.rules
   sudo udevadm control --reload-rules && sudo udevadm trigger
   ```

7. **Configure CarBrain**
   - Edit `carbrain/carbrain.py`:
     ```python
     USE_REAL_OBD = True
     OBD_PORT = "/dev/rfcomm0"  # or "/dev/ttyUSB0"
     ```
   - Adjust `modules/config.py` poll/log intervals if needed.

8. **Test manually**
   ```bash
   cd ~/OBD_CAR
   python3 carbrain/carbrain.py
   ```

---

## 2. Autostart the Application on Power‑up

There are several options; the simplest is to use a `systemd` service.

1. **Create a service unit**
   ```bash
   sudo tee /etc/systemd/system/carbrain.service > /dev/null <<'EOF'
[Unit]
Description=CarBrain OBD dashboard
After=network.target bluetooth.service

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/OBD_CAR
ExecStart=/usr/bin/python3 /home/pi/OBD_CAR/carbrain/carbrain.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF
   ```

2. **Enable and start**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable carbrain.service
   sudo systemctl start carbrain.service    # test it now
   sudo systemctl status carbrain.service   # verify running
   ```

3. **Optional display config**
   - If running in full‑screen kiosk mode you may want to auto‑login and
     start X with the app, using `~/.bash_profile` or `~/.xsession`.
   - The `CarBrain` code already has `self.overrideredirect(True)` for kiosk.

4. **Power‑cycle test**
   - Reboot the Pi and observe that CarBrain starts by itself and the screen
     shows home view.

---

### Notes
- Logs from the service appear in `journalctl -u carbrain.service`.
- To update the application, pull the latest code and restart the service:
  `sudo systemctl restart carbrain.service`.
- If you prefer a cron `@reboot` job or GUI autostart file, those are
  alternative methods but `systemd` is the most reliable.

Feel free to copy this file to the Pi or include it in the repo for future reference.