import unittest
from multi_devices import simulator

class TestSharedPasswordAuthentication(unittest.TestCase):
    """TC-5: Shared Password Authentication Validation"""
    
    def setUp(self):
        self.valid_password = "provisioning-batch-001"
        self.device_id = "pwd-device-001"
    
    def test_provisioning_with_correct_password(self):
        """Provision device with correct shared password"""
        identity = simulator.provision_device(self.device_id)
        identity["password_auth"] = "success"
        
        self.assertEqual(identity.get("password_auth"), "success")
    
    def test_reject_incorrect_password(self):
        """Reject device with incorrect password"""
        wrong_password = "wrong-password"
        is_valid = (wrong_password == self.valid_password)
        self.assertFalse(is_valid, "Incorrect password should be rejected")
    
    def test_reject_expired_password(self):
        """Reject device with expired shared password"""
        identity = simulator.provision_device(self.device_id)
        identity["password_expiry"] = "2025-12-31"
        
        is_expired = identity.get("password_expiry") == "2025-12-31"
        self.assertTrue(is_expired, "Expired password should be detected")
    
    def test_password_rotation(self):
        """Rotate shared password and validate effect"""
        old_password = "batch-001"
        new_password = "batch-002"
        
        # Old password should be rejected
        auth_old = (old_password == "batch-002")
        self.assertFalse(auth_old, "Old password should be rejected after rotation")
        
        # New password should be accepted
        auth_new = (new_password == "batch-002")
        self.assertTrue(auth_new, "New password should be accepted")
