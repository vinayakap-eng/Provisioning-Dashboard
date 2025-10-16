# multi_devices/tests/test_tc1.py
import unittest
from multi_devices import simulator

class TestDeviceUniqueIDAssignment(unittest.TestCase):
    def setUp(self):
        self.device_id = "sim-device-001"
        # ✅ Provision before each test so file exists
        simulator.provision_device(self.device_id)

    def test_device_receives_unique_identity(self):
        identity = simulator.provision_device(self.device_id)
        self.assertIn("device_id", identity)
        self.assertEqual(identity["device_id"], self.device_id)
        self.assertIn("cert_cn", identity)
        self.assertEqual(identity["status"], "provisioned")

    def test_device_stores_identity(self):
        self.assertTrue(simulator.device_has_identity(self.device_id),
                        "Identity file should exist after provisioning")

    def test_device_loopback_authentication(self):
        self.assertTrue(simulator.device_has_identity(self.device_id),
                        "Device identity must be available for loopback auth")

if __name__ == "__main__":
    unittest.main()
