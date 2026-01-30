#!/usr/bin/env python3
"""
Raspberry Pi Device Self-Enrollment Script
Run this on your Pi to automatically enroll with the CA server
"""

import os
import sys
import subprocess
import json
import socket
import ssl
import urllib.request
import urllib.error
import requests

def get_device_ip():
    """Get Pi's IP address"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "192.168.68.116"

def generate_csr(device_id):
    """Generate Certificate Signing Request"""
    print(f"[1] Generating CSR for device: {device_id}")
    # Generate an unencrypted private key and CSR (-nodes avoids passphrase prompt)
    cmd = [
        "openssl", "req", "-newkey", "rsa:2048", "-nodes",
        "-keyout", f"{device_id}.key",
        "-out", f"{device_id}.csr",
        "-subj", f"/CN={device_id}/O=IoT/C=US"
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ CSR generation failed: {result.stderr}")
        return False
    
    print(f"✅ CSR generated: {device_id}.csr")
    return True

def enroll_with_ca(device_id, ca_url):
    """Send CSR to CA server using multipart form upload and receive certificate"""
    print(f"[2] Enrolling with CA: {ca_url}")

    csr_file = f"{device_id}.csr"
    cert_file = f"{device_id}.crt"

    if not os.path.exists(csr_file):
        print(f"❌ CSR file not found: {csr_file}")
        return False

    try:
        # Use multipart/form-data with field name 'csr' as the CA expects
        with open(csr_file, 'rb') as f:
            files = {'csr': ('device.csr', f, 'application/octet-stream')}
            resp = requests.post(f"{ca_url}/enroll", files=files, verify=False, timeout=30)

        if resp.status_code != 200:
            print(f"❌ CA returned HTTP {resp.status_code}: {resp.text[:200]}")
            return False

        # Save certificate
        with open(cert_file, 'wb') as out:
            out.write(resp.content)

        print(f"✅ Certificate received: {cert_file}")
        return True

    except Exception as e:
        print(f"❌ Enrollment failed: {e}")
        return False

def create_config(device_id):
    """Create device configuration file"""
    print(f"[3] Creating configuration")
    
    config = {
        "device_id": device_id,
        "certificate": f"{device_id}.crt",
        "private_key": f"{device_id}.key",
        "ca_url": "https://192.168.68.107:5000",
        "status": "enrolled"
    }
    
    with open("device_config.json", "w") as f:
        json.dump(config, f, indent=2)
    
    print(f"✅ Config created: device_config.json")
    return True

def main():
    print("=" * 60)
    print("IoT Device Self-Enrollment")
    print("=" * 60)
    
    # Get device IP
    device_ip = get_device_ip()
    device_id = f"device-{device_ip.replace('.', '-')}"
    
    print(f"\n📱 Device IP: {device_ip}")
    print(f"📱 Device ID: {device_id}\n")
    
    # CA Server URL (change to your computer's IP)
    ca_url = "https://192.168.68.107:5000"
    
    # Step 1: Generate CSR
    if not generate_csr(device_id):
        sys.exit(1)
    
    # Step 2: Enroll with CA
    if not enroll_with_ca(device_id, ca_url):
        sys.exit(1)
    
    # Step 3: Create config
    if not create_config(device_id):
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("✅ Device enrollment complete!")
    print("=" * 60)
    print(f"\nFiles created:")
    print(f"  - {device_id}.key (private key)")
    print(f"  - {device_id}.crt (certificate)")
    print(f"  - device_config.json (configuration)")
    print(f"\nYour device is now ready for secure communication!")

if __name__ == "__main__":
    main()
