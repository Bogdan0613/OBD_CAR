# CarBrain - Mazda 3 2008 OBD Integration Setup

## Overview
This project integrates real OBD-II scanner functionality with a Mazda 3 2008 1.6 BK, optimized for Raspberry Pi 5 deployment.

## Hardware Requirements
- Raspberry Pi 5
- ELM327 Bluetooth or USB OBD-II adapter
- 3.5" touchscreen display
- Mazda 3 2008 1.6 BK (or compatible OBD-II vehicle)

## Software Setup

### 1. Install Dependencies
```bash
# Run the setup script
chmod +x setup_rpi_obd.sh
./setup_rpi_obd.sh
```

### 2. Connect ELM327 Adapter

#### Bluetooth ELM327:
```bash
# Scan for devices
hcitool scan

# Pair and bind (replace XX:XX:XX:XX:XX:XX with your adapter's MAC)
sudo rfcomm bind /dev/rfcomm0 XX:XX:XX:XX:XX:XX
```

#### USB ELM327:
- Plug in the USB adapter
- Device appears as `/dev/ttyUSB0` automatically

### 3. Configure CarBrain
Edit `carbrain.py`:
```python
USE_REAL_OBD = True
OBD_PORT = "/dev/rfcomm0"  # or "/dev/ttyUSB0" for USB
```

### 4. Run the Application
```bash
python3 carbrain.py
```

## Mazda 3 2008 Specific Notes

### OBD-II Compatibility
- **Protocol**: ISO 9141-2 (common for 2008 Mazda vehicles)
- **No Odometer Support**: Kilometers calculated from speed over time
- **Fuel Calculation**: Uses MAF (Mass Air Flow) sensor data
- **Supported PIDs**: RPM, Coolant Temp, Engine Load, Throttle Position, Speed, MAF, Intake Pressure, Intake Temp, Battery Voltage

### Fuel Consumption Accuracy
- Primary method: MAF sensor with stoichiometric ratio (14.7:1)
- Fallback method: Engine load and RPM estimation
- Real-time calculation ensures accurate trip fuel tracking

### Distance Calculation
Since the Mazda 3 2008 doesn't provide odometer readings via OBD-II:
- Distance calculated: `speed (km/h) × time (hours)`
- Integrated over polling intervals for accuracy
- Minimum trip distance threshold: 0.001 km

## Troubleshooting

### Connection Issues
```bash
# Check Bluetooth status
sudo systemctl status bluetooth

# Test OBD connection
python3 -c "
import obd
obd.logger.setLevel('DEBUG')
o = obd.OBD('/dev/rfcomm0')
print('Status:', o.status())
print('Supported commands:', len(o.supported_commands))
"
```

### Common Issues
1. **No OBD connection**: Check ELM327 power and vehicle ignition
2. **Permission denied**: Ensure proper device permissions
3. **No data**: Verify correct protocol for Mazda 3 2008
4. **Inaccurate fuel readings**: Check MAF sensor calibration

## Performance Optimizations
- Polling interval: 1000ms (balanced responsiveness vs. CPU usage)
- Logging interval: 30 seconds (frequent enough for accuracy)
- Thread-safe data access with locks
- Error handling for missing OBD responses

## Development Notes
- Uses `python-obd` library (most reliable Python OBD-II library)
- Tkinter GUI optimized for 480×320 touchscreen
- SQLite database for trip storage
- Real-time telemetry logging during trips