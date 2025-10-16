# send_telemetry.py
import time
import json
from azure.iot.device import IoTHubDeviceClient, Message

# ---------------------------
# CONFIG - replace this line
# ---------------------------
CONNECTION_STRING = "HostName=amrita-iothub01.azure-devices.net;DeviceId=sim-device-001;SharedAccessKey=NTWGgxUYMYH6UP34rQjM9irO5TqmZi/ZI/0uudBshBzn50AIlmB6wDj3kkrRl0EiamScZyKKNn88AIoT3lLp8g=="

# Optionally: you can also set CONNECTION_STRING via environment variable and read os.environ

def main():
    print("Creating IoT Hub device client from connection string...")
    client = IoTHubDeviceClient.create_from_connection_string(CONNECTION_STRING)

    print("Connecting to IoT Hub...")
    client.connect()
    print("✅ Connected.")

    try:
        count = 0
        while True:
            # example telemetry payload — you can customize fields
            payload = {
                "deviceId": "sim-device-001",
                "msgId": count,
                "temperature": round(20 + (5 * (time.time() % 6) / 6), 2),
                "humidity": round(40 + (10 * (time.time() % 8) / 8), 2),
                "ts": int(time.time())
            }
            msg = Message(json.dumps(payload))
            msg.content_type = "application/json"
            msg.content_encoding = "utf-8"

            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Sending: {payload}")
            client.send_message(msg)
            print("→ Sent")
            count += 1
            time.sleep(5)  # send every 5 seconds

    except KeyboardInterrupt:
        print("Stopped by user")
    except Exception as e:
        print("Error while sending:", e)
    finally:
        try:
            client.disconnect()
        except:
            pass
        print("Disconnected")

if __name__ == "__main__":
    main()
