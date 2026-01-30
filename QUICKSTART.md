C# Quick Start: Setting Up Real Raspberry Pi with IoT Monitoring

**Complete beginner guide - follow step by step**

---

## Part 1: What You Need

### Hardware
- [ ] 1x Raspberry Pi (any model: Pi 4, Pi 3B+, Pi Zero, etc.)
- [ ] Micro SD card (16GB minimum)
- [ ] Power supply for Pi
- [ ] Network cable or WiFi (to connect to your network)
- [ ] Your main computer (Windows/Mac/Linux)

### Software (on your main computer)
- [ ] This project (provisioning-dashboard) running
- [ ] CA server running on port 5000
- [ ] Python 3 installed

### Network Setup
- Your Raspberry Pi and main computer must be on the **same WiFi/network**
- Get your main computer's IP address (NOT localhost or 127.0.0.1)

---

## Part 2: Getting Your Machine's IP Address

This is **CRITICAL** - you need this to connect your Pi to your server.

### Windows (PowerShell)
```powershell
ipconfig
```

Look for **"IPv4 Address"** - it usually looks like:
```
192.168.1.100
10.0.0.50
172.16.0.25
```

**Copy this IP address - you'll need it later!**

### Mac (Terminal)
```bash
ifconfig | grep "inet " | grep -v 127.0.0.1
```

### Linux (Terminal)
```bash
hostname -I
```

**IMPORTANT:** 
- ❌ Don't use `localhost` or `127.0.0.1`
- ✓ Use the actual IP like `192.168.1.100`
- ✓ Make sure Pi can ping this address

---

## Part 3: Start Your CA Server

On your main computer, **must be running**:

### Step 1: Open terminal/PowerShell
Navigate to your project folder:
```powershell
cd C:\Users\CSN-IOT-ADMIN\CertificateMonitor\provisioning-dashboard
```

### Step 2: Start CA server
```powershell
# Start the CA enroll server (it listens on port 5000 and serves the /enroll endpoint)
python server/app.py
```

You should see log output indicating Flask started and is using the CA SSL certs (the server is configured to bind to all interfaces on port 5000).

> If your Raspberry Pi is on a different machine, ensure your firewall allows incoming TCP on port 5000.

**Note:** the Django development server you run for the dashboard (see Part 13) is HTTP-only by default. The telemetry script posts to the dashboard using plain HTTP (port 8000). If you want HTTPS for the dashboard, run Django behind a TLS-terminating proxy (nginx, Caddy) or use a dev tool that provides HTTPS.

**Leave this running in the terminal!**

---

## Part 4: Install Raspberry Pi OS

### If you have a NEW Raspberry Pi:

1. Download **Raspberry Pi Imager**: https://www.raspberrypi.com/software/
2. Insert SD card into computer
3. Open Raspberry Pi Imager
4. Select:
   - **Operating System**: Raspberry Pi OS (Full)
   - **Storage**: Your SD card
   - Click **Write** (this takes ~5 min)
5. Insert SD card into Pi and power on
6. Wait ~2 minutes for first boot

### If you already have Raspberry Pi OS:
- Skip to Part 5

---

## Part 5: Set Up Pi (First Time)

When your Pi boots up for the first time:

1. **Choose Language & Timezone**
2. **Create Password** - remember this! You'll use it for `ssh`
3. **Connect to WiFi** - select your home WiFi
4. **Check for updates** - let it update

Write down your login:
```
Username: pi
Password: [what you set]
```

---

## Part 6: Find Your Pi's IP Address

On the Pi, go to:
- Top-right corner → Network icon → click it
- Look for something like: **192.168.1.150**

Or use your router's admin panel to find it.

**Write this down too!**
```
Pi IP: 192.168.1.150
Your Machine IP: 192.168.1.100
```

---

## Part 7: Connect to Pi via SSH

On your main computer, open PowerShell:

```powershell
# Windows
ssh pi@192.168.1.150

# Mac/Linux
ssh pi@192.168.1.150
```

Type "yes" when asked, then enter your Pi password.

You should now see:
```
pi@raspberrypi:~$
```

**You're now inside your Pi!**

---

## Part 8: Install Requirements on Pi

Still in the SSH terminal, run these commands **one by one**:

```bash
# Update system packages
sudo apt update
sudo apt upgrade -y

# Install OpenSSL (likely already there)
sudo apt install openssl -y

# Install Python packages
pip3 install requests psutil
```

This takes a few minutes. Wait for each to finish.

---

## Part 9: Upload Scripts to Pi

### From your main computer (new PowerShell window):

```powershell
# Copy enrollment script
scp raspi_device_setup.py pi@192.168.1.150:/home/pi/

# Copy telemetry script
scp raspi_device_telemetry.py pi@192.168.1.150:/home/pi/
```

Type "yes" and your Pi password when prompted.

---

## Part 10: Edit Configuration (Still on Pi in SSH)

Edit the setup script to use YOUR machine's IP:

```bash
# Edit the file
nano raspi_device_setup.py
```

Find line 18 that says:
```python
CA_SERVER = "https://192.168.1.100:5000"
```

Change `192.168.1.100` to **YOUR machine's IP address**

Also change `raspi-01` to a device name (keeps it as is for first device)

Then:
- Press `Ctrl + X`
- Press `Y` to save
- Press `Enter` to confirm

---

## Part 11: Enroll Your Pi (Register with CA)

Still on your Pi via SSH:

```bash
python3 raspi_device_setup.py
```

Watch for output like:
```
✅ ENROLLMENT SUCCESSFUL!
Device ID: raspi-01
Certificate: /home/pi/.iot_device/raspi-01.crt
```

**If you see errors:**
- Check your machine's IP is correct
- Make sure CA server is still running on your computer
- Make sure firewall allows port 5000

---


## Part 12: Start Telemetry Service

Still on your Pi via SSH:

```bash
python3 raspi_device_telemetry.py
```

You should see:
```
[2025-01-12 14:23:45] Device ID: raspi-01
[2025-01-12 14:23:45] ✓ Connection successful!
[2025-01-12 14:23:47] Temp: 54.3°C | Memory: 18.2% | Uptime: 0d 0h 2m
```

**Leave this running!** It will send data every 30 seconds.

> **Note:** The telemetry API performs basic validation and will reject malformed payloads. Ensure your telemetry payload includes:
> - `device_id` (required)
> - `timestamp` in ISO 8601 format (e.g. `2025-01-12T14:23:45Z`) if present
> - `sensors` as a JSON object (if present)
>
> Invalid payloads return HTTP 400 and are logged on the server.

---

## Part 13: See Your Device in Dashboard

Open your web browser on your main computer:

```
http://localhost:8000/  (or http://localhost:8000/dashboard)
```

You should see:
- Device name: `raspi-01`
- Status: **Online**
- Sensor readings updating (see **Sensors** column) — hover the sensors value to view the full sensor payload JSON
- Certificate info

---

## Part 14: Keep It Running (Optional but Recommended)

If you want the Pi to keep sending data **after restart**, go back to Pi SSH and:

```bash
# Create startup service
sudo nano /etc/systemd/system/iot-telemetry.service
```

Paste this:
```ini
[Unit]
Description=IoT Device Telemetry Service
After=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi
ExecStart=/usr/bin/python3 /home/pi/raspi_device_telemetry.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Then:
```bash
# Enable it
sudo systemctl enable iot-telemetry.service

# Start it
sudo systemctl start iot-telemetry.service

# Check status
sudo systemctl status iot-telemetry.service
```

Now it runs on boot automatically!

---

## Common Issues & Fixes

### "Connection refused" or "Cannot reach server"
**Fix:**
- [ ] CA server running on your machine? (`python app.py`)
- [ ] Using correct IP? (not `localhost`)
- [ ] IP address is correct? (check `ipconfig`)
- [ ] Firewall allows port 5000?

### "ModuleNotFoundError: No module named 'requests'"
**Fix:**
```bash
pip3 install requests psutil
```

### "openssl: command not found"
**Fix:**
```bash
sudo apt install openssl -y
```

### Running UI Tests (Selenium)

If you want to run automated UI tests that verify modal behavior and cert download handling:

1. Install dev requirements:

```bash
pip3 install -r requirements-dev.txt
```

2. Run the Django test for UI:

```bash
python manage.py test multi_devices.tests.test_ui.DashboardUITest
```

Notes:
- Tests require Chrome and will use webdriver-manager to download a compatible chromedriver. If Chrome is not available on your runner, the test will be skipped.
- These tests run a headless browser and interact with the live Django test server.

### Device shows offline in dashboard
**Fix:**
- Telemetry script still running on Pi?
- Pi connected to network?
- Check Pi logs:
  ```bash
  sudo systemctl status iot-telemetry.service
  ```

### Too slow / device won't boot
**Fix:**
- Pi 4 is recommended (Pi Zero might be slow)
- Fresh Raspberry Pi OS installation
- Check SD card speed (Class 10 recommended)

---

## What's Actually Happening

```
┌─────────────────────────────┐
│   Your Main Computer        │
│  ┌─────────────────────┐   │
│  │  CA Server          │   │
│  │  Port: 5000         │   │
│  │  (issues certs)     │   │
│  └─────────────────────┘   │
│  ┌─────────────────────┐   │
│  │  Dashboard          │   │
│  │  Port: 8000         │   │
│  │  (shows data)       │   │
│  └─────────────────────┘   │
└─────────────────────────────┘
          ↕ (mTLS)
┌─────────────────────────────┐
│  Raspberry Pi               │
│  ┌─────────────────────┐   │
│  │ Telemetry Script    │   │
│  │ ├─ Reads CPU temp   │   │
│  │ ├─ Reads memory     │   │
│  │ ├─ Reads disk       │   │
│  │ └─ Sends every 30s  │   │
│  └─────────────────────┘   │
└─────────────────────────────┘
```

**In simple terms:**
1. Pi registers itself with your CA (gets a certificate)
2. Pi reads its own sensors (temp, memory, etc.)
3. Pi sends encrypted data to your server every 30 seconds
4. Your dashboard displays this real data
5. You can monitor the Pi's health in real-time

---

## Next Steps (After Setup Works)

- [ ] Add 2nd Raspberry Pi (repeat from Part 9)
- [ ] Set alerts for high CPU temp
- [ ] Monitor certificate expiry
- [ ] Set up automatic certificate rotation
- [ ] Create backups of certificates
- [ ] Enable production TLS (instead of self-signed)

---

## Getting Help

If something goes wrong:

1. **Check your IP addresses** - most common issue
2. **Verify CA server is running** - must be on
3. **Read error messages carefully** - they tell you what's wrong
4. **Check network connectivity**:
   ```bash
   ping 192.168.1.100  # From Pi to your computer
   ```

---

**You're all set! Follow these steps in order and you'll have a real IoT device monitoring system running.**

Questions? Everything is in the script comments too!
