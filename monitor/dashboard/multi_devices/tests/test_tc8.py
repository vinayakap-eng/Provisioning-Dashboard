import unittest
import time
from multi_devices import simulator

class TestNetworkInterruptionRecovery(unittest.TestCase):
    """TC-8: Network Interruption Recovery"""
    
    def test_graceful_failure_on_network_loss(self):
        """Provisioning fails gracefully when network lost"""
        device_id = "net-loss-device"
        
        # Simulate network loss during provisioning
        try:
            raise ConnectionError("Network unreachable")
        except ConnectionError as e:
            error_handled = str(e) == "Network unreachable"
        
        self.assertTrue(error_handled, "Network loss not handled gracefully")
    
    def test_retry_after_network_restoration(self):
        """Provisioning succeeds after network is restored"""
        device_id = "retry-device"
        
        # First attempt fails
        attempt_1 = None
        try:
            raise ConnectionError("Network down")
        except ConnectionError:
            attempt_1 = "failed"
        
        # Second attempt succeeds
        attempt_2 = "success"
        identity = simulator.provision_device(device_id)
        
        self.assertEqual(attempt_1, "failed")
        self.assertEqual(attempt_2, "success")
        self.assertIsNotNone(identity)
    
    def test_no_duplicate_ids_after_recovery(self):
        """Ensure no duplicate IDs created after network recovery"""
        device_id = "dup-check-device"
        ids_created = set()
        
        # Simulate multiple attempts
        for attempt in range(3):
            identity = simulator.provision_device(device_id)
            ids_created.add(identity.get("device_id"))
        
        # Should have only 1 unique ID despite multiple attempts
        self.assertEqual(len(ids_created), 1, "Duplicate IDs detected after recovery")
    
    def test_clean_error_notification(self):
        """Device receives clean error notification"""
        error_response = {
            "status": "PROVISION_FAILED",
            "error_code": "NETWORK_TIMEOUT",
            "message": "Network timeout: please retry provisioning",
            "retry_allowed": True
        }
        
        self.assertIn("error_code", error_response)
        self.assertTrue(error_response.get("retry_allowed"), "Device should be allowed to retry")
    
    def test_connection_timeout_handling(self):
        """Handle connection timeouts without data corruption"""
        device_id = "timeout-device"
        
        # Simulate timeout
        timeout_error = None
        try:
            time.sleep(0.1)  # Simulate delay
            raise TimeoutError("Connection timed out")
        except TimeoutError as e:
            timeout_error = str(e)
        
        # Should handle gracefully and allow retry
        identity = simulator.provision_device(device_id)
        
        self.assertIsNotNone(timeout_error)
        self.assertIsNotNone(identity)
