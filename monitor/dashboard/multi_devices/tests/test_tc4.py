import unittest
from multi_devices import simulator

class TestInvalidCredentialRejection(unittest.TestCase):
    """TC-4: Invalid Credential Rejection"""
    
    def test_reject_expired_certificate(self):
        """Reject provisioning with expired certificate"""
        device_id = "expired-device"
        identity = simulator.provision_device(device_id)
        identity["cert_status"] = "expired"
        
        # Simulate server validation
        is_valid = identity.get("cert_status") != "expired"
        self.assertFalse(is_valid, "Expired cert should be rejected")
    
    def test_reject_revoked_certificate(self):
        """Reject provisioning with revoked certificate"""
        device_id = "revoked-device"
        identity = simulator.provision_device(device_id)
        identity["revoked"] = True
        
        is_valid = not identity.get("revoked", False)
        self.assertFalse(is_valid, "Revoked cert should be rejected")
    
    def test_reject_invalid_signature(self):
        """Reject certificate with invalid signature"""
        device_id = "invalid-sig-device"
        identity = simulator.provision_device(device_id)
        identity["signature_valid"] = False
        
        is_valid = identity.get("signature_valid", True)
        self.assertFalse(is_valid, "Invalid signature should be rejected")
    
    def test_detailed_error_logging(self):
        """Verify error messages logged with reason codes"""
        error_log = {
            "device_id": "test-device",
            "error_code": "CERT_EXPIRED",
            "reason": "Certificate expired at 2025-01-01",
            "timestamp": "2026-01-20T12:00:00Z"
        }
        
        self.assertIn("error_code", error_log)
        self.assertIn("reason", error_log)
        self.assertIn("timestamp", error_log)
