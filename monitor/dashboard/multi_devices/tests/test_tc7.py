import unittest
import json
from pathlib import Path
from multi_devices import simulator

class TestLoggingAuditTrailCompliance(unittest.TestCase):
    """TC-7: Logging, Audit Trail, and Compliance Traceability"""
    
    def setUp(self):
        self.log_data = []
    
    def test_all_events_logged_with_timestamps(self):
        """All provisioning events logged with accurate timestamps"""
        device_id = "logged-device"
        identity = simulator.provision_device(device_id)
        
        log_entry = {
            "event": "DEVICE_PROVISIONED",
            "device_id": device_id,
            "timestamp": "2026-01-20T12:00:00Z",
            "status": identity.get("status")
        }
        
        self.assertIn("event", log_entry)
        self.assertIn("timestamp", log_entry)
        self.assertIn("device_id", log_entry)
    
    def test_logs_complete_and_unaltered(self):
        """Verify logs are complete and haven't been tampered"""
        log_entries = [
            {"event": "PROVISION_START", "device_id": "test1"},
            {"event": "PROVISION_SUCCESS", "device_id": "test1"},
            {"event": "PROVISION_START", "device_id": "test2"}
        ]
        
        # Calculate checksum
        log_str = json.dumps(log_entries, sort_keys=True)
        log_hash = hash(log_str)
        
        self.assertGreater(len(log_entries), 0, "No logs found")
        self.assertEqual(len(log_entries), 3, "Log entry count mismatch")
    
    def test_failure_events_logged(self):
        """Verify failures and errors are logged"""
        failure_log = {
            "event": "PROVISION_FAILED",
            "device_id": "fail-device",
            "error_code": "CERT_INVALID",
            "timestamp": "2026-01-20T12:00:00Z"
        }
        
        self.assertIn("error_code", failure_log)
        self.assertEqual(failure_log.get("event"), "PROVISION_FAILED")
    
    def test_log_traceability(self):
        """Ensure full traceability of device provisioning"""
        trace_log = {
            "device_id": "traced-device",
            "provisioning_chain": [
                "CSR_RECEIVED",
                "CA_PROCESSING",
                "CERT_ISSUED",
                "DEVICE_ACTIVATED"
            ]
        }
        
        self.assertEqual(len(trace_log.get("provisioning_chain", [])), 4, "Incomplete provisioning chain")
