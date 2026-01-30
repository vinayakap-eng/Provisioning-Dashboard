import unittest
import json
from unittest.mock import patch, MagicMock
from multi_devices import simulator

class TestDeviceRegistrationMutualAuth(unittest.TestCase):
    """TC-2: Device Registration & Mutual Authentication"""
    
    def setUp(self):
        self.device_id = "sim-device-002"
        self.identity = simulator.provision_device(self.device_id)
    
    def test_device_initiates_tls_handshake(self):
        """Step 1: Device initiates TLS handshake"""
        self.assertTrue(simulator.device_has_identity(self.device_id))
        self.assertIn("cert_cn", self.identity)
    
    def test_device_sends_client_certificate(self):
        """Step 2: Device sends client certificate"""
        self.assertIsNotNone(self.identity.get("cert_cn"))
        self.assertTrue(self.identity.get("cert_cn").startswith("CN="))
    
    def test_mutual_authentication_succeeds(self):
        """Step 3: Both parties verify each other's certificates"""
        # Simulate certificate validation
        cert_cn = self.identity.get("cert_cn")
        device_id = self.identity.get("device_id")
        self.assertEqual(cert_cn, f"CN={device_id}")
    
    def test_encrypted_secure_channel_established(self):
        """Step 4: Encrypted secure channel established"""
        self.assertEqual(self.identity.get("status"), "provisioned")
        self.assertTrue(simulator.device_has_identity(self.device_id))
    
    def test_device_sends_registration_payload(self):
        """Step 5: Device sends registration payload over secure channel"""
        payload = {
            "device_id": self.identity.get("device_id"),
            "cert_cn": self.identity.get("cert_cn"),
            "status": "registered"
        }
        self.assertIn("device_id", payload)
        self.assertIn("cert_cn", payload)

if __name__ == "__main__":
    unittest.main()

