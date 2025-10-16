import nmap, socket, ssl

# Step A: Scan LAN
import nmap
import os

def scan_network(subnet):
    # Tell python-nmap where to find nmap.exe
    nmap_path = r"C:\Program Files (x86)\Nmap\nmap.exe"
    nm = nmap.PortScanner(nmap_search_path=(nmap_path,))
    nm.scan(hosts=subnet, arguments='-sn')
    devices = []
    for host in nm.all_hosts():
        devices.append({
            "ip": host,
            "hostname": nm[host].hostname(),
            "mac": nm[host]['addresses'].get('mac', 'N/A')
        })
    return devices


# Step B: Check if device accepts mTLS
def check_mtls(ip, port=443, cert_file="certs/client.crt", key_file="certs/client.key", ca_file="certs/ca.crt"):
    try:
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=ca_file)
        context.load_cert_chain(certfile=cert_file, keyfile=key_file)
        context.check_hostname = False

        with socket.create_connection((ip, port), timeout=3) as sock:
            with context.wrap_socket(sock, server_hostname=ip) as ssock:
                return {"mtls_status": True}
    except Exception:
        return {"mtls_status": False}