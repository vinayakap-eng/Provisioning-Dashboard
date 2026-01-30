import unittest
import threading
import time
from multi_devices import simulator

class TestBulkOnboardingRaceConditions(unittest.TestCase):
    """TC-3: Bulk Onboarding & Race Condition Error Handling"""
    
    def test_concurrent_provisioning_100_devices(self):
        """Test simultaneous provisioning of 100 devices"""
        num_devices = 100
        device_ids = [f"bulk-device-{i:03d}" for i in range(num_devices)]
        provisioned = []
        errors = []
        
        def provision_device_thread(device_id):
            try:
                identity = simulator.provision_device(device_id)
                provisioned.append(identity.get("device_id"))
            except Exception as e:
                errors.append((device_id, str(e)))
        
        # Create threads for concurrent provisioning
        threads = []
        for device_id in device_ids:
            t = threading.Thread(target=provision_device_thread, args=(device_id,))
            threads.append(t)
            t.start()
        
        # Wait for all threads to complete
        for t in threads:
            t.join()
        
        # Verify results
        self.assertEqual(len(errors), 0, f"Errors during provisioning: {errors}")
        self.assertEqual(len(provisioned), num_devices, f"Expected {num_devices} provisioned, got {len(provisioned)}")
        self.assertEqual(len(set(provisioned)), num_devices, "Device IDs are not unique!")
    
    def test_no_id_collisions(self):
        """Verify IDs remain unique under concurrent load"""
        device_ids = set()
        for i in range(50):
            device_id = f"concurrent-{i}"
            identity = simulator.provision_device(device_id)
            device_ids.add(identity.get("device_id"))
        
        self.assertEqual(len(device_ids), 50, "ID collision detected!")
    
    def test_server_stability_under_load(self):
        """Verify server remains stable under load"""
        start_time = time.time()
        for i in range(100):
            simulator.provision_device(f"load-test-{i}")
        elapsed = time.time() - start_time
        
        # Should complete 100 provisions in reasonable time
        self.assertLess(elapsed, 30, f"Provisioning 100 devices took {elapsed}s (too slow)")
