#!/usr/bin/env python3
"""
Raspberry Pi Real Device Setup & Enrollment
This script provisions a real Raspberry Pi with certificates from the CA server
and enables it to connect securely to the monitoring dashboard.

Run this ONCE on your Raspberry Pi to enroll it.
"""

import os
import subprocess
import requests
import json
import socket
from pathlib import Path

# ============ CONFIGURATION ============
DEVICE_NAME = "raspi-01"  # Change this for each device: raspi-02, raspi-03, etc.
CA_SERVER = "https://192.168.68.107:5000"  # Change to your machine's IP (include :5000)
DEVICE_DIR = Path.home() / ".iot_device"
DEVICE_DIR.mkdir(exist_ok=True)

KEY_FILE = DEVICE_DIR / f"{DEVICE_NAME}.key"
CSR_FILE = DEVICE_DIR / f"{DEVICE_NAME}.csr"
CERT_FILE = DEVICE_DIR / f"{DEVICE_NAME}.crt"
CONFIG_FILE = DEVICE_DIR / "device_config.json"

# ============ FUNCTIONS ============

def log(msg, level="INFO"):
    print(f"[{level}] {msg}")

def get_device_info():
    """Gather Raspberry Pi hardware information"""
    try:
        hostname = socket.gethostname()
        mac_addr = open('/sys/class/net/eth0/address').read().strip()
        
        # Try to get serial number (only works on actual Raspberry Pi)
        try:
            serial = open('/proc/cpuinfo').read()
            serial = [l.split(':')[1].strip() for l in serial.split('\n') if 'Serial' in l][0]
        except:
            serial = "unknown"
            
        return {
            "hostname": hostname,
            "mac_address": mac_addr,
            "serial": serial
        }
    except Exception as e:
        log(f"Could not read device info: {e}", "WARN")
        return {"hostname": "rpi-device", "mac_address": "unknown", "serial": "unknown"}

def generate_key_and_csr():
    """Generate RSA key and Certificate Signing Request"""
    log(f"Generating RSA key for {DEVICE_NAME}...")
    
    # Generate 2048-bit private key
    subprocess.run([
        "openssl", "genrsa", "-out", str(KEY_FILE), "2048"
    ], check=True)
    log(f"✓ Key saved to {KEY_FILE}")
    
    # Gather device info for CSR
    device_info = get_device_info()
    log(f"Device Info: {json.dumps(device_info, indent=2)}")
    
    # Create CSR with device info in subject
    log("Generating Certificate Signing Request...")
    subprocess.run([
        "openssl", "req", "-new",
        "-key", str(KEY_FILE),
        "-out", str(CSR_FILE),
        "-subj", f"/CN={DEVICE_NAME}/O=RaspberryPi/C=US"
    ], check=True)
    log(f"✓ CSR saved to {CSR_FILE}")
    
    return device_info

def enroll_device(device_info, force=False):
    """Send CSR to CA server and get signed certificate"""
    log(f"Connecting to CA server: {CA_SERVER}")
    
    try:
        with open(CSR_FILE, 'rb') as f:
            csr_data = f.read()
        
        data = {"device_name": DEVICE_NAME}
        if force:
            data['force'] = 'true'
        # Send CSR to CA
        response = requests.post(
            f"{CA_SERVER}/enroll",
            files={"csr": csr_data},
            data=data,
            verify=False,
            timeout=10
        )
        
        if response.status_code == 200:
            # Save certificate
            with open(CERT_FILE, 'wb') as f:
                f.write(response.content)
            log(f"✓ Certificate received and saved to {CERT_FILE}")
            return True
        else:
            log(f"Enrollment failed: {response.status_code} - {response.text}", "ERROR")
            return False
    except requests.exceptions.ConnectionError:
        log(f"Cannot reach CA server at {CA_SERVER}", "ERROR")
        log("Make sure:", "ERROR")
        log("  1. Your CA server is running on port 5000", "ERROR")
        log(f"  2. Use your machine's actual IP (not localhost)", "ERROR")
        log("  3. Raspberry Pi can reach your machine (same network)", "ERROR")
        return False
    except Exception as e:
        log(f"Enrollment error: {e}", "ERROR")
        return False

def save_config(device_info):
    """Save device configuration for the telemetry script"""
    config = {
        "device_id": DEVICE_NAME,
        "ca_server": CA_SERVER,
        "cert_file": str(CERT_FILE),
        "key_file": str(KEY_FILE),
        "device_info": device_info,
        "enrolled_at": str(Path(CSR_FILE).stat().st_mtime)
    }
    
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)
    log(f"✓ Configuration saved to {CONFIG_FILE}")

def verify_enrollment():
    """Verify certificate is valid"""
    try:
        result = subprocess.run(
            ["openssl", "x509", "-in", str(CERT_FILE), "-text", "-noout"],
            capture_output=True,
            text=True,
            check=True
        )
        log("✓ Certificate is valid and readable")
        
        # Extract subject CN
        for line in result.stdout.split('\n'):
            if 'Subject:' in line:
                log(f"Certificate Subject: {line.strip()}")
        return True
    except Exception as e:
        log(f"Certificate verification failed: {e}", "ERROR")
        return False

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Enroll Raspberry Pi device with CA')
    parser.add_argument('--force', action='store_true', help='Force re-enrollment by revoking existing cert if present')
    args = parser.parse_args()

    log("=" * 60)
    log("Raspberry Pi IoT Device Enrollment")
    log("=" * 60)
    
    # Step 1: Check prerequisites
    log("\n[Step 1] Checking prerequisites...")
    try:
        subprocess.run(["openssl", "version"], capture_output=True, check=True)
        log("✓ OpenSSL is installed")
    except:
        log("OpenSSL not found! Install with: sudo apt install openssl", "ERROR")
        return False
    
    try:
        import requests
        log("✓ Python requests module is available")
    except:
        log("Requests module not found! Install with: pip3 install requests", "ERROR")
        return False
    
    # Step 2: Generate key and CSR
    log("\n[Step 2] Generating device credentials...")
    device_info = generate_key_and_csr()
    
    # Step 3: Enroll with CA
    log("\n[Step 3] Enrolling with Certificate Authority...")
    if not enroll_device(device_info, force=args.force):
        return False
    
    # Step 4: Verify
    log("\n[Step 4] Verifying enrollment...")
    if not verify_enrollment():
        return False
    
    # Step 5: Save config
    log("\n[Step 5] Saving configuration...")
    save_config(device_info)
    
    # Success!
    log("\n" + "=" * 60)
    log("✅ ENROLLMENT SUCCESSFUL!")
    log("=" * 60)
    log(f"\nDevice ID: {DEVICE_NAME}")
    log(f"Certificate: {CERT_FILE}")
    log(f"Config: {CONFIG_FILE}")
    log("\nNext steps:")
    log("1. Download raspi_device_telemetry.py to the same directory")
    log("2. Run: python3 raspi_device_telemetry.py")
    log("3. Monitor your device in the web dashboard at:")
    log(f"   http://{CA_SERVER.replace('https://','').replace('http://','').replace(':5000','')}:8080/dashboard")
    
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
