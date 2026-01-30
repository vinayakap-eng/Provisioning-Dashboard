#!/usr/bin/env python3
"""
Raspberry Pi Real Device Telemetry & Monitoring
This script runs on a Raspberry Pi and continuously sends sensor data
to the monitoring dashboard using mTLS authentication.

Prerequisites:
- Run raspi_device_setup.py first to enroll the device
- Install: pip3 install requests psutil
"""

import json
import time
import requests
import socket
from pathlib import Path
from datetime import datetime
import subprocess
import threading

# ============ CONFIGURATION ============
CONFIG_FILE = Path.home() / ".iot_device" / "device_config.json"
TELEMETRY_INTERVAL = 30  # Send data every 30 seconds
DASHBOARD_PORT = 8000  # Django dashboard port

# ============ LOAD CONFIGURATION ============
if not CONFIG_FILE.exists():
    print("❌ Configuration not found!")
    print("Please run raspi_device_setup.py first")
    exit(1)

with open(CONFIG_FILE) as f:
    config = json.load(f)

DEVICE_ID = config["device_id"]
CA_SERVER = config["ca_server"]
CERT_FILE = config["cert_file"]
KEY_FILE = config["key_file"]

print(f"Loaded config for device: {DEVICE_ID}")
print(f"CA Server: {CA_SERVER}")

# ============ SENSOR READING FUNCTIONS ============

def read_cpu_temp():
    """Read CPU temperature (Raspberry Pi specific)"""
    try:
        with open('/sys/class/thermal/thermal_zone0/temp') as f:
            temp_millidegrees = float(f.read())
            return round(temp_millidegrees / 1000, 2)
    except:
        # Fallback for other systems
        try:
            result = subprocess.run(
                ["vcgencmd", "measure_temp"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                temp_str = result.stdout.strip()
                return float(temp_str.split('=')[1].replace("'C", ""))
        except:
            return None

def read_cpu_usage():
    """Read CPU usage percentage"""
    try:
        import psutil
        return psutil.cpu_percent(interval=1)
    except:
        try:
            result = subprocess.run(
                ["top", "-bn1"],
                capture_output=True,
                text=True,
                timeout=5
            )
            # This is a simplified version
            return None
        except:
            return None

def read_memory_usage():
    """Read memory usage"""
    try:
        import psutil
        return {
            "used_percent": psutil.virtual_memory().percent,
            "used_mb": psutil.virtual_memory().used // (1024 * 1024),
            "total_mb": psutil.virtual_memory().total // (1024 * 1024)
        }
    except:
        try:
            with open('/proc/meminfo') as f:
                lines = f.readlines()
                mem_total = int([l for l in lines if 'MemTotal' in l][0].split()[1])
                mem_available = int([l for l in lines if 'MemAvailable' in l][0].split()[1])
                used = mem_total - mem_available
                return {
                    "used_percent": round((used / mem_total) * 100, 2),
                    "used_mb": round(used / 1024, 2),
                    "total_mb": round(mem_total / 1024, 2)
                }
        except:
            return None

def read_uptime():
    """Read system uptime"""
    try:
        with open('/proc/uptime') as f:
            uptime_seconds = float(f.read().split()[0])
            days = int(uptime_seconds // 86400)
            hours = int((uptime_seconds % 86400) // 3600)
            minutes = int((uptime_seconds % 3600) // 60)
            return f"{days}d {hours}h {minutes}m"
    except:
        return None

def read_disk_usage():
    """Read disk usage"""
    try:
        import shutil
        stat = shutil.disk_usage('/')
        return {
            "used_percent": round((stat.used / stat.total) * 100, 2),
            "used_gb": round(stat.used / (1024**3), 2),
            "total_gb": round(stat.total / (1024**3), 2)
        }
    except:
        return None

def read_network_info():
    """Read network information"""
    try:
        hostname = socket.gethostname()
        interfaces = socket.getaddrinfo(hostname, None)
        ips = list(set([ip[-1][0] for ip in interfaces]))
        return {
            "hostname": hostname,
            "ips": ips
        }
    except:
        return None

def read_gpio_status():
    """Check if GPIO pins are accessible (indicates healthy Raspberry Pi)"""
    try:
        with open('/sys/class/gpio/export', 'w') as f:
            f.write('4')  # Try to export GPIO 4
        return True
    except:
        return False

# ============ TELEMETRY COLLECTION ============

def collect_telemetry():
    """Collect all sensor data"""
    return {
        "device_id": DEVICE_ID,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "status": "online",
        "sensors": {
            "cpu": {
                "temp_celsius": read_cpu_temp(),
                "usage_percent": read_cpu_usage()
            },
            "memory": read_memory_usage(),
            "disk": read_disk_usage(),
            "system": {
                "uptime": read_uptime()
            },
            "network": read_network_info(),
            "gpio": {
                "accessible": read_gpio_status()
            }
        }
    }

# ============ SEND DATA TO DASHBOARD ============

def send_telemetry(telemetry_data):
    """Send telemetry to dashboard using mTLS"""
    try:
        # Endpoint 1: Send to CA monitoring endpoint
        response1 = requests.post(
            f"{CA_SERVER}/telemetry",
            json=telemetry_data,
            cert=(CERT_FILE, KEY_FILE),
            verify=False,
            timeout=10
        )
        
            # Endpoint 2: Send to Django dashboard (use HTTP - dev server is HTTP)
        from urllib.parse import urlparse
        parsed = urlparse(CA_SERVER)
        host = parsed.hostname or CA_SERVER.replace('https://','').replace('http://','').split(':')[0]
        dashboard_url = f"http://{host}:{DASHBOARD_PORT}"

        try:
            response2 = requests.post(
                f"{dashboard_url}/api/device-telemetry/",
                json=telemetry_data,
                timeout=10
            )
        except Exception:
            response2 = None
            # don't raise here; we'll rely on response1 (CA server) or log later
        
        # Determine success safely (response2 may be None)
        try:
            success = ((response1 is not None and getattr(response1, 'status_code', None) == 200)
                       or (response2 is not None and getattr(response2, 'status_code', None) == 200))
        except Exception:
            success = False
        return bool(success)
        
    except requests.exceptions.ConnectionError as e:
        print(f"⚠️ Connection error: {e}")
        return False
    except requests.exceptions.Timeout:
        print("⚠️ Connection timeout")
        return False
    except Exception as e:
        print(f"⚠️ Error sending telemetry: {e}")
        return False
        return False

# ============ CERTIFICATE HEALTH CHECK ============

def check_certificate_health():
    """Check if certificate is still valid"""
    try:
        result = subprocess.run(
            ["openssl", "x509", "-in", CERT_FILE, "-noout", "-checkend", "0"],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0  # 0 = valid, non-zero = expired
    except:
        return False

def get_certificate_expiry():
    """Get certificate expiry date"""
    try:
        result = subprocess.run(
            ["openssl", "x509", "-in", CERT_FILE, "-noout", "-enddate"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except:
        return None

# ============ MAIN LOOP ============

def log(msg, level="INFO"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {msg}")

def monitor_certificate():
    """Monitor certificate health in background"""
    while True:
        time.sleep(3600)  # Check every hour
        is_valid = check_certificate_health()
        expiry = get_certificate_expiry()
        
        if not is_valid:
            log("⚠️ CERTIFICATE EXPIRED OR INVALID", "ALERT")
        else:
            log(f"✓ Certificate valid - Expires: {expiry}", "OK")

def main():
    log("=" * 70)
    log("Raspberry Pi IoT Device Telemetry Service", "START")
    log("=" * 70)
    log(f"Device ID: {DEVICE_ID}")
    log(f"CA Server: {CA_SERVER}")
    log(f"Send interval: {TELEMETRY_INTERVAL} seconds")
    
    # Start certificate monitoring in background
    cert_monitor = threading.Thread(target=monitor_certificate, daemon=True)
    cert_monitor.start()
    
    # Check initial connection
    log("Testing connection to CA server...")
    telemetry_data = collect_telemetry()
    if send_telemetry(telemetry_data):
        log("✅ Connection successful!", "OK")
    else:
        log("⚠️ Could not reach CA server - will retry", "WARN")
    
    # Main telemetry loop
    log("Starting telemetry collection...", "START")
    send_count = 0
    error_count = 0
    
    try:
        while True:
            telemetry_data = collect_telemetry()
            
            # Log sensor data
            cpu_temp = telemetry_data["sensors"]["cpu"]["temp_celsius"]
            memory = telemetry_data["sensors"]["memory"]
            uptime = telemetry_data["sensors"]["system"]["uptime"]
            
            log_msg = f"Temp: {cpu_temp}°C | Memory: {memory['used_percent'] if memory else 'N/A'}% | Uptime: {uptime}"
            log(log_msg)
            
            # Send to dashboard
            if send_telemetry(telemetry_data):
                send_count += 1
                if send_count % 10 == 0:
                    log(f"✓ Telemetry sent ({send_count} total)", "OK")
            else:
                error_count += 1
                if error_count % 5 == 0:
                    log(f"⚠️ Send failures: {error_count}", "WARN")
            
            time.sleep(TELEMETRY_INTERVAL)
            
    except KeyboardInterrupt:
        log("\nShutdown requested by user", "STOP")
        log(f"Stats - Sent: {send_count}, Errors: {error_count}", "STAT")
        exit(0)
    except Exception as e:
        log(f"Unexpected error: {e}", "ERROR")
        exit(1)

if __name__ == "__main__":
    main()
