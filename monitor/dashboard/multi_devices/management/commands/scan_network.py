from django.core.management.base import BaseCommand
from multi_devices.scanner import scan_network
import ipaddress


class Command(BaseCommand):
    help = "Scan network (TLS certificates) and persist device info"

    def add_arguments(self, parser):
        parser.add_argument("--subnet", default="192.168.1.0/24", help="CIDR to scan")
        parser.add_argument("--port", default=443, type=int, help="Port to scan (default 443)")

    def handle(self, *args, **options):
        subnet = options["subnet"]
        port = options["port"]
        net = ipaddress.ip_network(subnet, strict=False)
        ip_count = len(list(net.hosts()))
        self.stdout.write(f"Scanning {ip_count} addresses from {subnet} on port {port} ...")
        scan_network(subnet=subnet, port=port)
        self.stdout.write("Scan complete.")
