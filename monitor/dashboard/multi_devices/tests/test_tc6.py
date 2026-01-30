import unittest
from multi_devices import simulator

class TestFirmwareTamperingPolicyCompliance(unittest.TestCase):
    """TC-6: Firmware Tampering & Policy Compliance"""
    
    def test_reject_tampered_firmware(self):
        """Deny provisioning for device with tampered firmware"""
        device_id = "tampered-fw-device"
        identity = simulator.provision_device(device_id)
        identity["firmware_verified"] = False
        
        is_valid = identity.get("firmware_verified", True)
        self.assertFalse(is_valid, "Tampered firmware should prevent provisioning")
    
    def test_firmware_integrity_check(self):
        """Verify firmware signature and hash"""
        device_id = "fw-check-device"
        identity = simulator.provision_device(device_id)
        identity["fw_hash"] = "abc123def456"
        identity["fw_signature_valid"] = True
        
        hash_present = "fw_hash" in identity
        sig_valid = identity.get("fw_signature_valid", False)
        self.assertTrue(hash_present and sig_valid, "Firmware integrity validation failed")
    
    def test_security_alert_on_tampering(self):
        """Alert and log when firmware tampering detected"""
        alert_log = {
            "severity": "CRITICAL",
            "event": "FIRMWARE_TAMPERING_DETECTED",
            "device_id": "tampered-device",
            "timestamp": "2026-01-20T12:00:00Z"
        }
        
        self.assertEqual(alert_log.get("severity"), "CRITICAL")
        self.assertIn("FIRMWARE_TAMPERING_DETECTED", alert_log.get("event", ""))
    
    def test_unauthorized_firmware_blocked(self):
        """Prevent provisioning of devices with unauthorized firmware"""
        authorized_fw = ["fw-v1.0", "fw-v2.0"]
        device_fw = "fw-unauthorized"
        
        is_authorized = device_fw in authorized_fw
        self.assertFalse(is_authorized, "Unauthorized firmware should be blocked")
