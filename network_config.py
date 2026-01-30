"""
Network configuration helper for real device scanning and provisioning.
Detects your local network and configures the scanner.
"""

import socket
import subprocess
import json
from pathlib import Path

def get_local_ip():
    """Get your machine's local IP address"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception as e:
        print(f"Error getting local IP: {e}")
        return None

def get_network_subnet(ip):
    """Convert IP to /24 subnet (e.g., 192.168.1.100 -> 192.168.1.0/24)"""
    parts = ip.split('.')
    return f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"

def check_nmap_installed():
    """Check if nmap is installed"""
    try:
        result = subprocess.run(['nmap', '--version'], capture_output=True, text=True)
        return "Nmap version" in result.stdout
    except FileNotFoundError:
        return False

def get_config():
    """Get network configuration"""
    local_ip = get_local_ip()
    subnet = get_network_subnet(local_ip) if local_ip else "192.168.1.0/24"
    nmap_installed = check_nmap_installed()
    
    config = {
        "local_ip": local_ip,
        "subnet": subnet,
        "nmap_installed": nmap_installed,
        "ca_server": "https://localhost:5000",
        "dashboard_server": "http://localhost:8000"
    }
    
    return config

def print_config():
    """Print network configuration"""
    config = get_config()
    print("\n" + "="*60)
    print("NETWORK CONFIGURATION")
    print("="*60)
    print(f"Your Local IP:     {config['local_ip']}")
    print(f"Scan Subnet:       {config['subnet']}")
    print(f"nmap Installed:    {'✅ Yes' if config['nmap_installed'] else '❌ No'}")
    print(f"CA Server:         {config['ca_server']}")
    print(f"Dashboard:         {config['dashboard_server']}")
    print("="*60 + "\n")
    
    if not config['nmap_installed']:
        print("⚠️  nmap is not installed. Install it with:")
        print("   Windows: choco install nmap")
        print("   Or download from: https://nmap.org/download.html\n")
    
    return config

if __name__ == "__main__":
    print_config()
