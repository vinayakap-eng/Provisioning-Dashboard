import os
import json
import subprocess
import platform
import re
import io, unittest, json
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from .tests_runner import run_all_tests

from .scanner import scan_network, check_mtls


# ----------------------------
# Utility: Parse certificate
# ----------------------------
def parse_certificate(cert_path):
    try:
        with open(cert_path, "rb") as f:
            cert_data = f.read()
        cert = x509.load_pem_x509_certificate(cert_data, default_backend())
        cn = cert.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)[0].value
        valid_from = cert.not_valid_before.isoformat()
        valid_to = cert.not_valid_after.isoformat()
        return cn, valid_from, valid_to
    except Exception:
        return "Unknown", "N/A", "N/A"


# ----------------------------
# Utility: Measure latency
# ----------------------------
def measure_latency(ip):
    try:
        system = platform.system().lower()
        if "windows" in system:
            cmd = ["ping", "-n", "1", ip]
        else:
            cmd = ["ping", "-c", "1", ip]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)

        if result.returncode == 0:
            # Regex to capture "time=23ms", "time<1ms", "time=23.4 ms"
            match = re.search(r"time[=<]?\s*(\d+\.?\d*)", result.stdout.lower())
            if match:
                return float(match.group(1))
        return None
    except Exception as e:
        print("Latency error:", e)
        return None


# ----------------------------
# Scan Devices View
# ----------------------------
def scan_devices_view(request):
    devices = scan_network("192.168.1.0/24")  # adjust subnet
    results = []
    for dev in devices:
        ip = dev["ip"]
        mtls_result = check_mtls(ip)
        results.append({
            "ip": ip,
            "hostname": dev["hostname"],
            "mac": dev["mac"],
            "status": "✅ Secure" if mtls_result["mtls_status"] else "❌ Unsecure"
        })
    return JsonResponse(results, safe=False)


# ----------------------------
# Provisioning Dashboard View
# ----------------------------
def dashboard_view(request):
    status_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "status.json"))

    if os.path.exists(status_file):
        with open(status_file, "r") as f:
            statuses = json.load(f)
    else:
        statuses = {}

    # Try to enrich devices with certificate info
    certs_dir = os.path.join(os.path.dirname(__file__), "certs")
    os.makedirs(certs_dir, exist_ok=True)

    for dev, data in statuses.items():
        cert_path = os.path.join(certs_dir, f"{dev}.crt")
        if os.path.exists(cert_path):
            cn, valid_from, valid_to = parse_certificate(cert_path)
            data["cn"] = cn
            data["valid_from"] = valid_from
            data["valid_to"] = valid_to
        else:
            data.setdefault("cn", "Unknown")
            data.setdefault("valid_from", "N/A")
            data.setdefault("valid_to", "N/A")

    # Count issues
    issues = sum(
        1 for data in statuses.values()
        if not (
            data.get("certificate_status", True)
            and data.get("key_status", True)
            and data.get("mtls_status", True)
            and data.get("mitm_status", True)
            and not data.get("revoked", False)
        )
    )

    alerts = []
    for dev, data in statuses.items():
        reasons = []
        if not data.get("certificate_status", True):
            reasons.append("Tampering")
        if not data.get("key_status", True):
            reasons.append("Key Issue")
        if not data.get("mtls_status", True):
            reasons.append("mTLS Failed")
        if not data.get("mitm_status", True):
            reasons.append("MITM Risk")
        if data.get("revoked", False):
            reasons.append("Revoked")
        if reasons:
            alerts.append(f"{dev} - {', '.join(reasons)}")

    return render(request, "dashboard.html", {
        "statuses": json.dumps(statuses),
        "statuses_json": statuses,
        "issues": issues,
        "uptime": "N/A",
        "alerts": alerts
    })


# ----------------------------
# Testcases View
# ----------------------------
def testcases_view(request):
    return render(request, "testcases.html")


# ----------------------------
# Provisioning API
# ----------------------------
# ----------------------------
# Provisioning API
# ----------------------------
@csrf_exempt
def provisioning_request_view(request):
    """
    Provision device automatically (CSR → signed cert → update status.json).
    """
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))
            ip = data.get("ip")

            if not ip:
                return JsonResponse({"error": "No IP provided"}, status=400)

            username = "Amrita3"
            base_dir = os.path.dirname(__file__)
            certs_dir = os.path.join(base_dir, "certs")
            os.makedirs(certs_dir, exist_ok=True)

            ca_cert = os.path.join(certs_dir, "ca.crt")
            ca_key = os.path.join(certs_dir, "ca.key")
            csr_local = os.path.join(certs_dir, f"{ip}.csr")
            cert_local = os.path.join(certs_dir, f"{ip}.crt")

            # 1. Copy CSR from Pi
            subprocess.run(
                ["scp", f"{username}@{ip}:/home/{username}/device.csr", csr_local],
                check=True
            )

            # 2. Sign CSR
            subprocess.run(
                ["openssl", "x509", "-req", "-in", csr_local,
                 "-CA", ca_cert, "-CAkey", ca_key, "-CAcreateserial",
                 "-out", cert_local, "-days", "365", "-sha256"],
                check=True
            )

            # 3. Send cert back to Pi
            subprocess.run(
                ["scp", cert_local, f"{username}@{ip}:/home/{username}/device.crt"],
                check=True
            )

            # 4. Parse CN + validity
            cn, valid_from, valid_to = parse_certificate(cert_local)

            # 5. Measure latency
            latency = measure_latency(ip)

            # 6. Update status.json
            status_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "status.json"))
            if os.path.exists(status_file):
                with open(status_file, "r") as f:
                    statuses = json.load(f)
            else:
                statuses = {}

            statuses[ip] = {
                "certificate_status": True,
                "key_status": True,
                "mtls_status": True,
                "mitm_status": True,
                "revoked": False,
                "cn": cn,
                "valid_from": valid_from,
                "valid_to": valid_to,
                "latency": latency if latency is not None else "N/A"
            }

            os.makedirs(os.path.dirname(status_file), exist_ok=True)
            with open(status_file, "w") as f:
                json.dump(statuses, f, indent=2)

            # ✅ Return full device info
            return JsonResponse({
                "success": True,
                "message": f"Provisioned {ip}",
                "ip": ip,
                "cn": cn,
                "valid_from": valid_from,
                "valid_to": valid_to,
                "latency": latency if latency is not None else "N/A"
            })

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request"}, status=400)
def run_testcases(request):
    """
    Discover and run all testcases under multi_devices/testcases
    """
    loader = unittest.TestLoader()
    suite = loader.discover('multi_devices/testcases')

    stream = io.StringIO()
    runner = unittest.TextTestRunner(stream=stream, verbosity=2)
    result = runner.run(suite)

    response = {
        "total": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "passed": result.testsRun - len(result.failures) - len(result.errors),
        "output": stream.getvalue(),
    }
    return JsonResponse(response)
def run_tests_view(request):
    """Endpoint to run all testcases"""
    data = run_all_tests()
    return JsonResponse(data)