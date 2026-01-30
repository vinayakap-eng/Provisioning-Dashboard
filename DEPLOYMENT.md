# Deployment Guide

## Quick Start - Local Testing

```bash
# 1. Clone repo
git clone https://github.com/yourusername/provisioning-dashboard.git
cd provisioning-dashboard

# 2. Setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
pip install gunicorn

# 3. Run locally
cd monitor/dashboard
python manage.py migrate
python manage.py runserver
```

## Deploy to Heroku

### Prerequisites
- Heroku account (free tier available)
- Heroku CLI installed
- GitHub account with repo

### Steps

```bash
# 1. Login to Heroku
heroku login

# 2. Create Heroku app
heroku create your-app-name

# 3. Set environment variables
heroku config:set SECRET_KEY='your-random-secret-key'
heroku config:set DEBUG=False
heroku config:set ALLOWED_HOSTS='your-app-name.herokuapp.com'

# 4. Deploy
git push heroku main
```

Your app will be available at: `https://your-app-name.herokuapp.com`

## Deploy to PythonAnywhere

### Steps

1. Sign up at https://www.pythonanywhere.com
2. Create new web app (choose Django)
3. Upload code via bash console:
   ```bash
   git clone https://github.com/yourusername/provisioning-dashboard.git
   ```
4. Configure WSGI file in Web tab
5. Set Python version to 3.10
6. Reload web app

## Deploy to DigitalOcean App Platform

1. Go to https://cloud.digitalocean.com/apps
2. Click **Create** → **App**
3. Connect GitHub repo
4. Set up:
   - **Build Command**: `pip install -r requirements-dev.txt && cd monitor/dashboard && python manage.py migrate`
   - **Run Command**: `cd monitor/dashboard && gunicorn iot_dashboard.wsgi --bind :8080`
5. Add environment variables in settings
6. Deploy

Your app will run on a public URL provided by DigitalOcean.

## Deploy to AWS EC2

### Launch Instance

1. EC2 → **Launch Instance**
2. Choose Ubuntu 20.04 LTS
3. Instance type: t2.micro (free tier)
4. Configure security group to allow HTTP (80) and HTTPS (443)

### Setup on Instance

```bash
# SSH into instance
ssh -i your-key.pem ubuntu@your-instance-ip

# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install dependencies
sudo apt-get install -y python3 python3-venv python3-pip git nginx supervisor openssl nmap

# Clone repo
git clone https://github.com/yourusername/provisioning-dashboard.git
cd provisioning-dashboard

# Setup Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
pip install gunicorn

# Run migrations
cd monitor/dashboard
python manage.py migrate
```

### Configure Nginx

Create `/etc/nginx/sites-available/dashboard`:

```nginx
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /static/ {
        alias /home/ubuntu/provisioning-dashboard/monitor/dashboard/staticfiles/;
    }
}
```

Enable it:
```bash
sudo ln -s /etc/nginx/sites-available/dashboard /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### Configure Supervisor

Create `/etc/supervisor/conf.d/dashboard.conf`:

```ini
[program:dashboard]
directory=/home/ubuntu/provisioning-dashboard/monitor/dashboard
command=/home/ubuntu/provisioning-dashboard/venv/bin/gunicorn iot_dashboard.wsgi -w 4 -b 127.0.0.1:8000
user=ubuntu
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/dashboard.log
```

Start it:
```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start dashboard
```

### Enable HTTPS with Let's Encrypt

```bash
sudo apt-get install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

## Monitor Your Deployment

### Heroku
```bash
heroku logs --tail
heroku ps
```

### PythonAnywhere
- Check logs in Web tab → Log files

### AWS EC2
```bash
sudo tail -f /var/log/dashboard.log
sudo supervisorctl status
```

## Troubleshooting

### App won't start
- Check logs
- Verify environment variables set
- Run migrations: `python manage.py migrate`

### 502 Bad Gateway
- Check gunicorn is running
- Check port is correct
- Verify firewall rules

### Can't connect to CA server
- If CA is on local machine, use proper URL
- For production, host CA separately or use managed CA service

## Next Steps

1. Set up custom domain name
2. Configure SSL certificates
3. Set up automated backups
4. Monitor application performance
5. Set up logging and alerts
