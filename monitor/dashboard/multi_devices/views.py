import os
import json
import subprocess
import platform
import re
import io, unittest, json
from datetime import datetime
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import logging
logger = logging.getLogger(__name__)
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
        # Use timezone-aware properties to avoid deprecation warnings
        try:
            valid_from = cert.not_valid_before_utc.isoformat()
            valid_to = cert.not_valid_after_utc.isoformat()
        except AttributeError:
            # Fallback for older cryptography versions
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
# Status helpers (shared)
# ----------------------------
STATUS_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'status.json'))

def load_statuses():
    try:
        if os.path.exists(STATUS_FILE):
            with open(STATUS_FILE, 'r') as f:
                return json.load(f)
    except Exception:
        logger.exception("Failed to read status file")
    return {}


def normalize_statuses(raw_statuses):
    out = {}
    for dev, data in (raw_statuses or {}).items():
        data = dict(data) if isinstance(data, dict) else {}
        # Ensure keys
        data.setdefault('certificate_status', data.get('certificate_status', False))
        data.setdefault('key_status', data.get('key_status', False))
        data.setdefault('mtls_status', data.get('mtls_status', False))
        data.setdefault('mitm_status', data.get('mitm_status', False))
        data.setdefault('revoked', data.get('revoked', False))
        data.setdefault('cn', data.get('cn', 'Unknown'))
        data.setdefault('valid_from', data.get('valid_from', 'N/A'))
        data.setdefault('valid_to', data.get('valid_to', 'N/A'))
        data.setdefault('latency', data.get('latency', 'N/A'))

        # Compute issue reasons
        reasons = []
        if not data.get('certificate_status'):
            reasons.append('Cert Failed')
        if not data.get('key_status'):
            reasons.append('Key Missing')
        if not data.get('mtls_status'):
            reasons.append('mTLS Failed')
        if not data.get('mitm_status'):
            reasons.append('MITM Risk')
        if data.get('revoked'):
            reasons.append('Revoked')

        data['issue_reasons'] = reasons
        if reasons:
            data['row_class'] = 'table-warning' if 'MITM Risk' in reasons else 'table-danger'
        else:
            data['row_class'] = ''

        # Sensors summary
        sensors = data.get('sensors') or {}
        sensor_summary = 'N/A'
        sensor_json = ''
        if isinstance(sensors, dict) and sensors:
            cpu = sensors.get('cpu', {})
            mem = sensors.get('memory', {})
            disk = sensors.get('disk', {})
            parts = []
            temp = cpu.get('temp_celsius')
            if isinstance(temp, (int, float)):
                parts.append(f"{temp:.1f}°C")
            usage = cpu.get('usage_percent')
            if isinstance(usage, (int, float)) and usage:
                parts.append(f"CPU {usage:.0f}%")
            memp = mem.get('used_percent')
            if isinstance(memp, (int, float)):
                parts.append(f"Mem {memp:.0f}%")
            diskp = disk.get('used_percent')
            if isinstance(diskp, (int, float)):
                parts.append(f"Disk {diskp:.0f}%")
            if parts:
                sensor_summary = ' · '.join(parts)
                try:
                    sensor_json = json.dumps(sensors)
                except Exception:
                    sensor_json = str(sensors)

        data['sensor_summary'] = sensor_summary
        data['sensors_json'] = sensor_json

        out[dev] = data
    return out


# ----------------------------
# Scan Devices View
# ----------------------------
def scan_devices_view(request):
    """Scan the local network for devices using nmap"""
    try:
        # Auto-detect subnet from local IP
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        
        # Convert to /24 subnet
        parts = local_ip.split('.')
        subnet = f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"
        
        logger.info(f"Scanning network: {subnet}")
        devices = scan_network(subnet)
        
        results = []
        for dev in devices:
            ip = dev["ip"]
            try:
                # Skip your own IP
                if ip == local_ip:
                    continue
                
                mtls_result = check_mtls(ip)
                results.append({
                    "ip": ip,
                    "hostname": dev.get("hostname", "unknown"),
                    "mac": dev.get("mac", "N/A"),
                    "status": "✅ Secure" if mtls_result.get("mtls_status") else "⏳ Needs Setup"
                })
            except Exception as e:
                logger.debug(f"Error checking device {ip}: {e}")
                results.append({
                    "ip": ip,
                    "hostname": dev.get("hostname", "unknown"),
                    "mac": dev.get("mac", "N/A"),
                    "status": "⏳ Needs Setup"
                })
        
        logger.info(f"Found {len(results)} devices")
        return JsonResponse(results, safe=False)
    except Exception as e:
        logger.exception(f"Scan error: {e}")
        return JsonResponse({"error": str(e)}, status=500)


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

    for dev, data in list(statuses.items()):
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

        # Normalize expected keys to avoid template errors
        data.setdefault("certificate_status", True)
        data.setdefault("key_status", True)
        data.setdefault("mtls_status", True)
        data.setdefault("mitm_status", True)
        data.setdefault("revoked", False)
        data.setdefault("latency", "N/A")

        # Compute issue reasons for better display
        reasons = []
        if not data.get("certificate_status"):
            reasons.append("Tampering")
        if not data.get("key_status"):
            reasons.append("Key Issue")
        if not data.get("mtls_status"):
            reasons.append("mTLS Failed")
        if not data.get("mitm_status"):
            reasons.append("MITM Risk")
        if data.get("revoked"):
            reasons.append("Revoked")

        data["issue_reasons"] = reasons
        # Add row class for styling
        if reasons:
            if "MITM Risk" in reasons:
                data["row_class"] = "table-warning"
            else:
                data["row_class"] = "table-danger"
        else:
            data["row_class"] = ""

        # Summarize sensors for display (e.g., "43.5°C · Mem 7% · Disk 6%")
        sensors = data.get("sensors") or {}
        sensor_summary = "N/A"
        sensor_json = ""
        if isinstance(sensors, dict) and sensors:
            cpu = sensors.get("cpu", {})
            mem = sensors.get("memory", {})
            disk = sensors.get("disk", {})
            parts = []
            temp = cpu.get("temp_celsius")
            if isinstance(temp, (int, float)):
                parts.append(f"{temp:.1f}°C")
            usage = cpu.get("usage_percent")
            if isinstance(usage, (int, float)) and usage:
                parts.append(f"CPU {usage:.0f}%")
            memp = mem.get("used_percent")
            if isinstance(memp, (int, float)):
                parts.append(f"Mem {memp:.0f}%")
            diskp = disk.get("used_percent")
            if isinstance(diskp, (int, float)):
                parts.append(f"Disk {diskp:.0f}%")
            if parts:
                sensor_summary = " · ".join(parts)
                sensor_json = json.dumps(sensors)
        data["sensor_summary"] = sensor_summary
        data["sensors_json"] = sensor_json

    # Count issues
    issues = sum(1 for data in statuses.values() if data.get("issue_reasons"))

    # Build alert list (deduplicated and limited)
    alerts = []
    for dev, data in statuses.items():
        if data.get("issue_reasons"):
            alerts.append({"device": dev, "reasons": data["issue_reasons"]})

    # Limit displayed alerts to top 5
    display_alerts = alerts[:5]
    extra_alerts = max(0, len(alerts) - len(display_alerts))

    # Last updated time (most recent last_seen)
    last_seen_times = [s.get('last_seen') for s in statuses.values() if s.get('last_seen')]
    last_updated = max(last_seen_times) if last_seen_times else "N/A"

    # Normalize statuses for template usage
    normalized = normalize_statuses(statuses)

    # Count issues
    issues = sum(1 for data in normalized.values() if data.get("issue_reasons"))

    # Build alert list (deduplicated and limited)
    alerts = []
    for dev, data in normalized.items():
        if data.get("issue_reasons"):
            alerts.append({"device": dev, "reasons": data["issue_reasons"]})

    # Limit displayed alerts to top 5
    display_alerts = alerts[:5]
    extra_alerts = max(0, len(alerts) - len(display_alerts))

    # Last updated time (most recent last_seen)
    last_seen_times = [s.get('last_seen') for s in normalized.values() if s.get('last_seen')]
    last_updated = max(last_seen_times) if last_seen_times else "N/A"

    return render(request, "dashboard.html", {
        "statuses": json.dumps(normalized),
        "statuses_json": normalized,
        "issues": issues,
        "uptime": "N/A",
        "alerts": display_alerts,
        "extra_alerts": extra_alerts,
        "total_alerts": len(alerts),
        "last_updated": last_updated
    })


@csrf_exempt
def status_json_view(request):
    """Return the statuses JSON for AJAX polling"""
    if request.method == 'GET':
        raw = load_statuses()
        normalized = normalize_statuses(raw)
        return JsonResponse(normalized)
    return JsonResponse({"error": "Only GET allowed"}, status=405)


@csrf_exempt
def status_json_view(request):
    """Return the statuses JSON for AJAX polling"""
    if request.method == 'GET':
        return JsonResponse(statuses)
    return JsonResponse({"error": "Only GET allowed"}, status=405)


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
    """Provision device automatically (CSR → signed cert → update status.json).
    Requires SSH key authentication setup on the Pi.
    """
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))
            ip = data.get("ip")

            if not ip:
                return JsonResponse({"error": "No IP provided"}, status=400)

            logger.info(f"Provisioning request for IP: {ip}")

            username = "Amrita3"
            base_dir = os.path.dirname(__file__)
            certs_dir = os.path.join(base_dir, "certs")
            os.makedirs(certs_dir, exist_ok=True)

            ca_cert = os.path.join(certs_dir, "ca.crt")
            ca_key = os.path.join(certs_dir, "ca.key")
            csr_local = os.path.join(certs_dir, f"{ip}.csr")
            cert_local = os.path.join(certs_dir, f"{ip}.crt")

            logger.info(f"Copying CSR from {username}@{ip}:/home/{username}/device.csr")
            # 1. Copy CSR from Pi (using SSH key, no password)
            result = subprocess.run(
                ["scp", "-o", "StrictHostKeyChecking=no", 
                 f"{username}@{ip}:/home/{username}/device.csr", csr_local],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode != 0:
                raise Exception(f"SCP failed: {result.stderr}")

            logger.info(f"Signing CSR with CA")
            # 2. Sign CSR
            result = subprocess.run(
                ["openssl", "x509", "-req", "-in", csr_local,
                 "-CA", ca_cert, "-CAkey", ca_key, "-CAcreateserial",
                 "-out", cert_local, "-days", "365", "-sha256"],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode != 0:
                raise Exception(f"OpenSSL failed: {result.stderr}")

            logger.info(f"Copying certificate back to {username}@{ip}")
            # 3. Send cert back to Pi
            result = subprocess.run(
                ["scp", "-o", "StrictHostKeyChecking=no",
                 cert_local, f"{username}@{ip}:/home/{username}/device.crt"],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode != 0:
                raise Exception(f"SCP cert copy failed: {result.stderr}")

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
                "latency": latency if latency is not None else "N/A",
                "provisioned_at": str(datetime.now())
            }

            os.makedirs(os.path.dirname(status_file), exist_ok=True)
            with open(status_file, "w") as f:
                json.dump(statuses, f, indent=2)

            logger.info(f"Successfully provisioned {ip} with CN: {cn}")
            
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
            logger.exception(f"Provisioning error: {e}")
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request"}, status=400)


# ----------------------------
# Device Telemetry API
# ----------------------------
@csrf_exempt
def device_telemetry_view(request):
    """Accept device telemetry (JSON) and update monitor data/status.json"""
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))
            if not isinstance(data, dict):
                logger.warning("Telemetry: payload not JSON object")
                return JsonResponse({"error": "Invalid JSON payload"}, status=400)

            device_id = data.get("device_id") or data.get("device")
            if not device_id:
                logger.warning("Telemetry: missing device_id in payload")
                return JsonResponse({"error": "Missing device_id"}, status=400)

            # Validate timestamp
            ts = data.get("timestamp")
            try:
                if ts:
                    # Accept ISO format timestamps
                    from datetime import datetime
                    datetime.fromisoformat(ts.replace('Z', '+00:00'))
            except Exception:
                logger.warning("Telemetry: invalid timestamp for device %s: %s", device_id, ts)
                return JsonResponse({"error": "Invalid timestamp format"}, status=400)

            # Ensure sensors is an object
            sensors = data.get("sensors")
            if sensors is not None and not isinstance(sensors, dict):
                logger.warning("Telemetry: sensors not an object for device %s", device_id)
                return JsonResponse({"error": "Invalid sensors format"}, status=400)

            status_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "status.json"))
            os.makedirs(os.path.dirname(status_file), exist_ok=True)

            if os.path.exists(status_file):
                with open(status_file, "r") as f:
                    statuses = json.load(f)
            else:
                statuses = {}

            statuses[device_id] = {
                "last_seen": ts,
                "status": data.get("status", "online"),
                "sensors": sensors,
            }

            with open(status_file, "w") as f:
                json.dump(statuses, f, indent=2)

            logger.info("Telemetry accepted from %s", device_id)
            return JsonResponse({"success": True})
        except Exception:
            logger.exception("Telemetry endpoint error")
            return JsonResponse({"error": "Internal server error"}, status=500)

    return JsonResponse({"error": "Invalid request"}, status=400)


@csrf_exempt
def download_cert_view(request):
    """Return the certificate file for a device.
    Endpoint: /provisioning/download-cert/?device=<id>
    Looks in: ../../../server/device.crt, server/device_raw.crt, ca/newcerts/<serial>.pem
    """
    import os
    from django.http import FileResponse
    
    device = request.GET.get('device')
    if not device:
        return JsonResponse({"error": "Missing device parameter"}, status=400)

    # Try multiple locations where CA server might store certs
    base_dir = os.path.dirname(__file__)  # multi_devices/
    app_root = os.path.dirname(os.path.dirname(base_dir))  # dashboard/
    project_root = os.path.dirname(os.path.dirname(app_root))  # provisioning-dashboard/
    
    cert_paths = [
        os.path.join(project_root, "server", f"{device}.crt"),  # server/device.crt (clean)
        os.path.join(project_root, "server", "device.crt"),  # generic device.crt
        os.path.join(project_root, "server", "device_raw.crt"),  # server/device_raw.crt
        os.path.join(base_dir, "certs", f"{device}.crt"),  # multi_devices/certs/device.crt
    ]
    
    for cert_path in cert_paths:
        if os.path.exists(cert_path):
            logger.info(f"Downloading cert from {cert_path}")
            try:
                return FileResponse(open(cert_path, 'rb'), as_attachment=True, filename=f"{device}.crt")
            except Exception as e:
                logger.error(f"Error serving cert: {e}")
                return JsonResponse({"error": f"Error serving certificate: {str(e)}"}, status=500)
    
    logger.warning(f"Certificate not found for device {device}. Checked paths: {cert_paths}")
    return JsonResponse({"error": "Certificate not found"}, status=404)


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
    try:
        logger.info("Starting test suite execution...")
        data = run_all_tests()
        logger.info(f"Test suite complete: {data.get('total')} tests, {data.get('passed')} passed, {data.get('failures')} failed, {data.get('errors')} errors")
        return JsonResponse(data)
    except Exception as e:
        logger.exception(f"Error running tests: {e}")
        return JsonResponse({
            "error": str(e),
            "total": 0,
            "passed": 0,
            "failures": 0,
            "errors": 1,
            "output": f"Exception: {str(e)}\n{repr(e)}"
        }, status=500)


def test_cases_view(request):
    """Display individual test cases that can be run separately"""
    from .tests_runner import get_available_tests
    
    tests = get_available_tests()
    context = {
        'tests': tests,
        'total_tests': len(tests)
    }
    return render(request, 'test_cases.html', context)


def run_single_test_view(request, test_name):
    """API endpoint to run a single test case"""
    from .tests_runner import run_single_test
    
    try:
        logger.info(f"Running single test: {test_name}")
        data = run_single_test(test_name)
        return JsonResponse(data)
    except Exception as e:
        logger.exception(f"Error running test {test_name}: {e}")
        return JsonResponse({
            "error": str(e),
            "total": 0,
            "passed": 0,
            "failures": 0,
            "errors": 1,
            "output": f"Exception: {str(e)}"
        }, status=500)
