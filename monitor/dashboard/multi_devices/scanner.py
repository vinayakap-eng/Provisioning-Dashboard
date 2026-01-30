import nmap, socket, ssl
import logging

logger = logging.getLogger(__name__)

def scan_network(subnet=None):
    """
    Scan network for live devices using nmap.
    If subnet is None, defaults to 192.168.68.0/24 (your detected network)
    """
    if subnet is None:
        subnet = "192.168.68.0/24"  # Your actual network
    
    try:
        logger.info(f"Scanning network: {subnet}")
        nm = nmap.PortScanner()
        nm.scan(hosts=subnet, arguments='-sn -T4')  # Ping scan, faster
        
        devices = []
        for host in nm.all_hosts():
            try:
                hostname = socket.gethostbyaddr(host)[0]
            except:
                hostname = "unknown"
            
            devices.append({
                "ip": host,
                "hostname": hostname,
                "mac": nm[host]['addresses'].get('mac', 'N/A') if 'addresses' in nm[host] else 'N/A',
                "status": "up"
            })
        
        logger.info(f"Found {len(devices)} devices on {subnet}")
        return devices
    except Exception as e:
        logger.error(f"Network scan error: {e}")
        return []


# Step B: Check if device accepts mTLS
def check_mtls(ip, port=443, cert_file="certs/client.crt", key_file="certs/client.key", ca_file="certs/ca.crt"):
    """
    Check if device accepts mutual TLS connections.
    """
    try:
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=ca_file)
        context.load_cert_chain(certfile=cert_file, keyfile=key_file)
        context.check_hostname = False

        with socket.create_connection((ip, port), timeout=3) as sock:
            with context.wrap_socket(sock, server_hostname=ip) as ssock:
                return {"mtls_status": True}
    except Exception as e:
        logger.debug(f"mTLS check failed for {ip}: {e}")
        return {"mtls_status": False}