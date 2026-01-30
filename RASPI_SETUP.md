# Real Raspberry Pi IoT Device Setup Guide

This guide shows you how to set up a **real Raspberry Pi** as an actual IoT device that connects to your monitoring system.

## What Happens in the Real World

```
Real Raspberry Pi Hardware
        ↓
        ├─ Generates SSL Certificate & Private Key
        ├─ Enrolls with Certificate Authority (CA)
        ├─ Reads Real Sensors (CPU temp, memory, disk)
        ├─ Sends data every 30 seconds
        └─ All connections encrypted with mTLS
        ↓
Your Monitoring Server (localhost:5000)
        ↓
        ├─ Receives sensor data
        ├─ Stores in database
        ├─ Monitors certificate validity
        ├─ Detects tampering
        └─ Displays on web dashboard
```

## Prerequisites

### On Your Machine (Windows/Mac/Linux)
- CA server running on port 5000 (`python app.py`)
- Django dashboard running on port 8000
- Network accessible from Raspberry Pi (get your machine's IP: Windows `ipconfig`)

### On Raspberry Pi
- Raspberry Pi OS (Bullseye or newer recommended)
- Python 3.7+
- OpenSSL
- pip3 for packages

## Step-by-Step Setup

### 1. Prepare Your Machine
Get your local IP address:

**Windows (PowerShell):**
```powershell
ipconfig
# Look for "IPv4 Address" - usually 192.168.x.x or 10.0.x.x
```

**Mac/Linux:**
```bash
ifconfig
# Look for inet address
```

**Note:** Use this IP instead of `localhost` when running on Raspberry Pi!

### 2. Copy Files to Raspberry Pi

**Option A: Using SCP (SSH Copy)**
```bash
# On your machine
scp raspi_device_setup.py pi@<raspi-ip>:/home/pi/
scp raspi_device_telemetry.py pi@<raspi-ip>:/home/pi/
```

**Option B: Manual Copy**
- Copy `raspi_device_setup.py` to your Raspberry Pi's home directory
- Copy `raspi_device_telemetry.py` to the same location

### 3. Install Dependencies on Raspberry Pi

SSH into your Raspberry Pi:
```bash
ssh pi@<raspi-ip>
```

Install required packages:
```bash
# Update system
sudo apt update
sudo apt upgrade -y

# Install OpenSSL (usually already installed)
sudo apt install openssl -y

# Install Python packages
pip3 install requests psutil
```

### 4. Enroll Device with CA

Edit `raspi_device_setup.py` to set your machine's IP:

```python
# Line 18 - Change this:
CA_SERVER = "https://192.168.1.100:5000"  # ← Your machine's IP here!
DEVICE_NAME = "raspi-01"  # Name this device
```

Run enrollment script:
```bash
python3 raspi_device_setup.py
```

This will:
- ✓ Generate RSA private key
- ✓ Create Certificate Signing Request (CSR)
- ✓ Send CSR to your CA server
- ✓ Receive signed certificate back
- ✓ Save everything in `~/.iot_device/`

**Expected output:**
```
[INFO] Raspberry Pi IoT Device Enrollment
[INFO] Checking prerequisites...
[INFO] ✓ OpenSSL is installed
[INFO] ✓ Python requests module is available
[INFO] Generating RSA key for raspi-01...
[INFO] Generating Certificate Signing Request...
[INFO] Connecting to CA server: https://192.168.1.100:5000
[INFO] ✓ Certificate received and saved
[INFO] ✓ Certificate is valid and readable
[INFO] ✅ ENROLLMENT SUCCESSFUL!
```

### 5. Run Telemetry Service

On the Raspberry Pi, start the telemetry service:

```bash
python3 raspi_device_telemetry.py
```

This will:
- ✓ Read real CPU temperature
- ✓ Read memory and disk usage
- ✓ Read system uptime
- ✓ Send encrypted data every 30 seconds
- ✓ Monitor certificate health

**Expected output:**
```
[2025-01-12 14:23:45] [START] Raspberry Pi IoT Device Telemetry Service
[2025-01-12 14:23:45] Device ID: raspi-01
[2025-01-12 14:23:45] CA Server: https://192.168.1.100:5000
[2025-01-12 14:23:45] Send interval: 30 seconds
[2025-01-12 14:23:46] ✓ Connection successful!
[2025-01-12 14:23:47] Temp: 54.3°C | Memory: 18.2% | Uptime: 1d 3h 24m
[2025-01-12 14:23:48] ✓ Telemetry sent (1 total)
```

> **Note:** The dashboard shows a **Sensors** column with a concise summary (e.g., `43.5°C · Mem 7% · Disk 6%`). Hover a sensors cell to view the full sensor payload JSON for troubleshooting.


### 6. Run as Background Service (Optional but Recommended)

Create a systemd service so telemetry runs on boot:

```bash
# Create service file
sudo nano /etc/systemd/system/iot-telemetry.service
```

Paste this content:
```ini
[Unit]
Description=IoT Device Telemetry Service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi
ExecStart=/usr/bin/python3 /home/pi/raspi_device_telemetry.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable iot-telemetry.service
sudo systemctl start iot-telemetry.service

# Check status
sudo systemctl status iot-telemetry.service

# View logs
sudo journalctl -u iot-telemetry.service -f
```

## What Data Gets Sent?

Every 30 seconds, your Raspberry Pi sends:

```json
{
  "device_id": "raspi-01",
  "timestamp": "2025-01-12T14:23:47.123Z",
  "status": "online",
  "sensors": {
    "cpu": {
      "temp_celsius": 54.3,
      "usage_percent": 22.5
    },
    "memory": {
      "used_percent": 18.2,
      "used_mb": 456,
      "total_mb": 2048
    },
    "disk": {
      "used_percent": 45.6,
      "used_gb": 23.1,
      "total_gb": 64
    },
    "system": {
      "uptime": "1d 3h 24m"
    },
    "network": {
      "hostname": "raspberrypi",
      "ips": ["192.168.1.150"]
    }
  }
}
```

> Note: The server validates telemetry payloads. `device_id` is required. If provided, `timestamp` should be ISO 8601 (e.g., `2025-01-12T14:23:47Z`). `sensors` must be a JSON object. Malformed requests will be rejected with HTTP 400 and logged on the server.

## How Monitoring Works

Your dashboard monitors:

| Aspect | What it checks |
|--------|---|
| **Certificate** | Still valid? Not expired? Not revoked? |
| **Tamper Detection** | Certificate hash hasn't changed |
| **Security** | mTLS connection established |
| **Health** | CPU temp, memory usage, disk space |
| **Connectivity** | Device sends data regularly |
| **Latency** | How long requests take |

## Troubleshooting

### Connection refused / timeout
- Check if CA server is running: `python app.py` on your machine
- Verify IP address is correct (not `localhost`)
- Check firewall - port 5000 must be open
- Test from Raspberry Pi: `curl -k https://<your-ip>:5000/`

### Certificate enrollment fails
```bash
# Check OpenSSL
openssl version

# Check requests module
python3 -c "import requests; print(requests.__version__)"

# Check network
ping <your-machine-ip>
```

### Telemetry not appearing in dashboard
- Check service is running: `python3 raspi_device_telemetry.py`
- Check logs: `tail -f ~/.iot_device/device_config.json`
- Verify certificate exists: `ls -la ~/.iot_device/`
- Test connection: `curl -k --cert ~/.iot_device/raspi-01.crt --key ~/.iot_device/raspi-01.key https://<your-ip>:5000/telemetry`

### High CPU temperature
- Normal: 40-60°C under light load
- Warning: 60-80°C
- Critical: 80°C+ (may throttle)
- Solution: Better cooling, reduce workload

## Multiple Devices

To add a second Raspberry Pi:

1. Copy both scripts to the new Pi
2. Change `DEVICE_NAME` in `raspi_device_setup.py`:
   ```python
   DEVICE_NAME = "raspi-02"  # Different name
   ```
3. Run enrollment and telemetry as before
4. Dashboard automatically shows both devices

## Production Checklist

- [ ] CA certificate pinning (instead of `verify=False`)
- [ ] Rotate certificates before expiry
- [ ] Monitor disk space (fill up = device unusable)
- [ ] Set up alerts for high temps
- [ ] Enable TLS 1.3 where possible
- [ ] Use strong CA root password
- [ ] Backup device certificates
- [ ] Regular security updates on Pi

## Real-World Scenarios This Tests

✓ **Device Provisioning**: Automatic enrollment with PKI
✓ **mTLS Authentication**: Client certificates for secure comms
✓ **Certificate Tampering**: Detect if cert/key modified
✓ **Certificate Expiry**: Track validity periods
✓ **Revocation**: Handle compromised devices
✓ **Network Resilience**: Auto-retry on connection loss
✓ **Sensor Integration**: Real hardware monitoring
✓ **Fleet Management**: Multiple devices in one dashboard

