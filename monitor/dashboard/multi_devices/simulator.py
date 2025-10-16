# multi_devices/simulator.py
import os
import json
from pathlib import Path

# Where to store simulated device identities
DEVICE_STORAGE = Path(__file__).resolve().parent / "sim_devices"
DEVICE_STORAGE.mkdir(exist_ok=True)

def provision_device(device_id: str):
    """
    Simulate provisioning of a device.
    Returns a dict with the "identity" details.
    """
    identity_path = DEVICE_STORAGE / f"{device_id}.json"

    # simulate unique ID / certificate creation
    identity_data = {
        "device_id": device_id,
        "cert_cn": f"CN={device_id}",
        "status": "provisioned"
    }
    with open(identity_path, "w") as f:
        json.dump(identity_data, f)

    return identity_data


def device_has_identity(device_id: str) -> bool:
    """
    Check if device identity exists and is valid.
    """
    identity_path = DEVICE_STORAGE / f"{device_id}.json"
    return identity_path.exists()
