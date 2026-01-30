# IoT Certificate Provisioning Dashboard

A comprehensive web-based dashboard for managing IoT device certificate provisioning, enrollment, and monitoring using a Django backend with integrated CA (Certificate Authority) server.

## Features

- **Device Management**: Scan network, enroll, and monitor IoT devices
- **Certificate Provisioning**: Automatic CSR generation, signing, and certificate deployment
- **Network Scanning**: Auto-detect devices on your network using nmap
- **Real-time Monitoring**: Live device status, connectivity, and telemetry
- **Test Suite**: Comprehensive test cases for device enrollment and provisioning
- **Dashboard UI**: Bootstrap-based responsive interface with Chart.js analytics
- **Multi-device Support**: Handle multiple simultaneous device enrollments
- **Simulated Devices**: Test environment with bulk device simulation

## Project Structure

```
provisioning-dashboard/
├── monitor/dashboard/              # Main Django application
│   ├── iot_dashboard/             # Django project settings
│   ├── multi_devices/             # Multi-device management app
│   │   ├── views.py              # Dashboard views and API endpoints
│   │   ├── models.py             # Device status models
│   │   ├── scanner.py            # Network scanning logic
│   │   ├── tests_runner.py        # Test orchestration
│   │   └── simulator.py           # Device simulation
│   └── templates/                # HTML templates
│       ├── Dashboard.html        # Main dashboard
│       └── test_cases.html       # Test cases UI
├── server/                        # Flask-based CA (Certificate Authority)
│   └── app.py                    # CA server with /enroll endpoint
├── pi_enrollment.py               # Raspberry Pi device enrollment script
├── requirements-dev.txt           # Python dependencies
└── manage.py                      # Django management

```

## Prerequisites

- Python 3.8+
- Django 3.2+
- OpenSSL
- nmap (for network scanning)
- requests library

## Installation

### 1. Clone and Setup

```bash
git clone https://github.com/yourusername/provisioning-dashboard.git
cd provisioning-dashboard
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements-dev.txt
pip install django requests nmap-python
sudo apt-get install nmap openssl  # Linux/Pi
brew install nmap openssl          # macOS
```

### 4. Setup Django

```bash
cd monitor/dashboard
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

### 5. Start CA Server (separate terminal)

```bash
cd server
python app.py  # Runs on https://localhost:5000
```

## Usage

### Access Dashboard

Open your browser and navigate to:
```
http://localhost:8000
```

### Scan Devices

1. Click **Scan Network** button on dashboard
2. Devices on your network will appear in the table
3. Auto-detects IPv4 range (e.g., 192.168.68.0/24)

### Enroll Device

1. Select a device from the scan results
2. Click **Provision Device**
3. Device generates CSR and submits to CA
4. Certificate is installed on device automatically

### Run Tests

1. Click **Test Cases Dashboard**
2. Run individual tests or **Run All Tests**
3. View results and logs

## Raspberry Pi Setup

### On the Raspberry Pi:

```bash
# Install dependencies
sudo apt-get install openssl python3-requests python3-pip

# Run enrollment script
python3 pi_enrollment.py
```

The script will:
1. Generate an unencrypted private key and CSR
2. Submit CSR to CA server via multipart form upload
3. Receive and save signed certificate
4. Create device configuration

## API Endpoints

### Django Dashboard (port 8000)

- `GET /scan-devices/` - Scan network and return device list
- `POST /provision-device/` - Provision a device with certificate
- `GET /run-tests/` - Run all test suites
- `POST /run-test/` - Run individual test
- `GET /test-cases/` - Test cases dashboard

### CA Server (port 5000, HTTPS)

- `POST /enroll` - Submit CSR (multipart form field: `csr`) and receive signed certificate

## Configuration

### Device Scan Subnet

Edit `monitor/dashboard/multi_devices/scanner.py`:
```python
# Auto-detects local subnet, can be overridden:
SUBNET = "192.168.68.0/24"
```

### CA Server Settings

Edit `server/app.py`:
- Port: Default 5000
- SSL Certificate: `server/ca.crt` and `server/ca.key`
- OpenSSL CA path: `ca/` directory

## Hosting Options

### Option 1: Heroku (Cloud)

1. Install Heroku CLI
2. Create `Procfile`:
   ```
   web: cd monitor/dashboard && gunicorn iot_dashboard.wsgi
   ```
3. Create `runtime.txt`:
   ```
   python-3.10.11
   ```
4. Deploy:
   ```bash
   heroku create your-app-name
   git push heroku main
   ```

### Option 2: PythonAnywhere

1. Sign up at PythonAnywhere.com
2. Upload code via git
3. Configure web app and WSGI file
4. Set environment variables in web app settings

### Option 3: AWS (EC2)

1. Launch EC2 instance (Ubuntu)
2. Install dependencies
3. Deploy with gunicorn + Nginx:
   ```bash
   gunicorn -w 4 iot_dashboard.wsgi -b 0.0.0.0:8000
   ```

### Option 4: DigitalOcean App Platform

1. Connect GitHub repo
2. Specify build command: `pip install -r requirements-dev.txt`
3. Specify run command: `cd monitor/dashboard && python manage.py runserver 0.0.0.0:8000`

## Environment Variables

Create `.env` file:
```
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
SECRET_KEY=your-secret-key
CA_SERVER_URL=https://your-ca-server.com:5000
```

## Testing

Run the test suite:
```bash
cd monitor/dashboard
python manage.py test multi_devices
```

Or use the dashboard Test Cases UI.

## Troubleshooting

### Network Scan Not Finding Devices
- Ensure nmap is installed: `which nmap`
- Check firewall allows ICMP/port scanning
- Verify devices are on the same subnet

### Certificate Enrollment Fails
- Check CA server is running: `curl -k https://localhost:5000/`
- Verify multipart form is sent correctly
- Check CA logs in `server/app.py`

### Dashboard Not Showing
- Clear browser cache
- Check Django is running: `python manage.py runserver`
- Check for errors: `python manage.py check`

## Security Notes

⚠️ **Important for Production:**
- Replace self-signed CA certificates with valid certificates
- Set `DEBUG=False` in production
- Use strong `SECRET_KEY` in Django settings
- Configure `ALLOWED_HOSTS` properly
- Run behind HTTPS/TLS proxy
- Restrict access to dashboard with authentication

## License

MIT License - See LICENSE file

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review test case output
3. Check application logs in `monitor/dashboard/`

## Contributing

1. Fork the repository
2. Create feature branch
3. Commit changes
4. Push and create pull request
