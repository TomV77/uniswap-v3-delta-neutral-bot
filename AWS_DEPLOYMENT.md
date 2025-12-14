# AWS Deployment Guide - t3.small Instance

This guide provides step-by-step instructions for deploying the Delta-Neutral Hedging Bot on an AWS t3.small instance.

## AWS Instance Specifications

- **Instance Type**: t3.small
- **vCPUs**: 2
- **Memory**: 2 GB
- **OS**: Ubuntu 22.04 LTS (recommended)
- **Storage**: 20 GB EBS (minimum)

## Quick Setup - Copy & Paste Commands

### 1. Initial Server Setup

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install Python 3.11 and required tools
sudo apt install -y python3.11 python3.11-venv python3-pip git curl

# Install system dependencies
sudo apt install -y build-essential libssl-dev libffi-dev python3-dev

# Verify Python version
python3.11 --version
```

### 2. Create Bot User (Optional but Recommended)

```bash
# Create dedicated user for the bot
sudo adduser botuser --disabled-password --gecos ""

# Switch to bot user
sudo su - botuser
```

### 3. Clone Repository

```bash
# Clone the repository
cd ~
git clone https://github.com/TomV77/uniswap-v3-delta-neutral-bot.git
cd uniswap-v3-delta-neutral-bot

# Create virtual environment
python3.11 -m venv venv

# Activate virtual environment
source venv/bin/activate
```

### 4. Install Dependencies

```bash
# Install Python packages
pip install --upgrade pip
pip install -r requirements.txt

# Verify installation
python -c "from bot.main import DeltaNeutralBot; print('Installation successful!')"
```

### 5. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit environment file with your credentials
nano .env
# OR use vim: vim .env
```

**Important**: Fill in your actual credentials in the `.env` file (see `.env.example` for template)

### 6. Configure Bot Settings

```bash
# Copy config template
cp config.json config.local.json

# Edit configuration
nano config.local.json
```

### 7. Test the Bot

```bash
# Activate virtual environment (if not already active)
source venv/bin/activate

# Run examples to verify setup
python examples.py

# Run tests
python -m pytest tests/ -v

# Test bot initialization
python -c "from bot.main import DeltaNeutralBot; import os; os.environ.setdefault('CONFIG_FILE', 'config.local.json'); bot = DeltaNeutralBot(); print('Bot initialized successfully')"
```

### 8. Run Bot as Systemd Service

```bash
# Create systemd service file (run as root or with sudo)
sudo tee /etc/systemd/system/delta-bot.service > /dev/null <<EOF
[Unit]
Description=Delta-Neutral Hedging Bot
After=network.target

[Service]
Type=simple
User=botuser
WorkingDirectory=/home/botuser/uniswap-v3-delta-neutral-bot
Environment="PATH=/home/botuser/uniswap-v3-delta-neutral-bot/venv/bin"
ExecStart=/home/botuser/uniswap-v3-delta-neutral-bot/venv/bin/python -m bot.main config.local.json
Restart=always
RestartSec=10
StandardOutput=append:/home/botuser/uniswap-v3-delta-neutral-bot/bot.log
StandardError=append:/home/botuser/uniswap-v3-delta-neutral-bot/bot-error.log

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable delta-bot

# Start the service
sudo systemctl start delta-bot

# Check status
sudo systemctl status delta-bot
```

### 9. Monitor the Bot

```bash
# View live logs
tail -f ~/uniswap-v3-delta-neutral-bot/bot.log

# View error logs
tail -f ~/uniswap-v3-delta-neutral-bot/bot-error.log

# Check service status
sudo systemctl status delta-bot

# Restart service
sudo systemctl restart delta-bot

# Stop service
sudo systemctl stop delta-bot
```

## Security Best Practices

### Firewall Configuration

```bash
# Enable UFW firewall
sudo ufw enable

# Allow SSH (IMPORTANT: Do this first!)
sudo ufw allow 22/tcp

# Allow only necessary outbound connections
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Check firewall status
sudo ufw status
```

### Secure Environment File

```bash
# Set proper permissions on .env file
chmod 600 .env

# Ensure only owner can read private keys
ls -la .env  # Should show: -rw------- 1 botuser botuser
```

### SSH Key Authentication (Disable Password Login)

```bash
# On your local machine, generate SSH key if you don't have one
ssh-keygen -t ed25519 -C "your_email@example.com"

# Copy public key to server
ssh-copy-id -i ~/.ssh/id_ed25519.pub botuser@your-server-ip

# On server, disable password authentication
sudo nano /etc/ssh/sshd_config
# Set: PasswordAuthentication no
# Save and restart SSH
sudo systemctl restart sshd
```

## Monitoring & Maintenance

### Log Rotation

```bash
# Create log rotation config
sudo tee /etc/logrotate.d/delta-bot > /dev/null <<EOF
/home/botuser/uniswap-v3-delta-neutral-bot/*.log {
    daily
    rotate 7
    compress
    delaycompress
    notifempty
    create 0644 botuser botuser
    sharedscripts
    postrotate
        systemctl reload delta-bot > /dev/null 2>&1 || true
    endscript
}
EOF
```

### Automated Backups

```bash
# Create backup script
cat > ~/backup-config.sh <<'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/home/botuser/backups"
mkdir -p $BACKUP_DIR

# Backup configuration files
tar -czf $BACKUP_DIR/config_backup_$DATE.tar.gz \
    /home/botuser/uniswap-v3-delta-neutral-bot/.env \
    /home/botuser/uniswap-v3-delta-neutral-bot/config.local.json

# Keep only last 7 days of backups
find $BACKUP_DIR -name "config_backup_*.tar.gz" -mtime +7 -delete

echo "Backup completed: config_backup_$DATE.tar.gz"
EOF

chmod +x ~/backup-config.sh

# Add to crontab (daily backup at 2 AM)
(crontab -l 2>/dev/null; echo "0 2 * * * /home/botuser/backup-config.sh") | crontab -
```

### Health Checks

```bash
# Create health check script
cat > ~/check-bot-health.sh <<'EOF'
#!/bin/bash

# Check if service is running
if ! systemctl is-active --quiet delta-bot; then
    echo "ERROR: Bot service is not running!"
    sudo systemctl restart delta-bot
    echo "Service restarted at $(date)"
fi

# Check for recent errors in logs
ERRORS=$(tail -n 100 /home/botuser/uniswap-v3-delta-neutral-bot/bot-error.log | grep -c "ERROR")
if [ $ERRORS -gt 10 ]; then
    echo "WARNING: $ERRORS errors found in recent logs"
fi

echo "Health check completed at $(date)"
EOF

chmod +x ~/check-bot-health.sh

# Run health check every 5 minutes
(crontab -l 2>/dev/null; echo "*/5 * * * * /home/botuser/check-bot-health.sh >> /home/botuser/health-check.log 2>&1") | crontab -
```

## Updating the Bot

```bash
# Stop the service
sudo systemctl stop delta-bot

# Activate virtual environment
cd ~/uniswap-v3-delta-neutral-bot
source venv/bin/activate

# Backup current configuration
cp .env .env.backup
cp config.local.json config.local.json.backup

# Pull latest changes
git pull origin main

# Update dependencies if needed
pip install --upgrade -r requirements.txt

# Run tests
python -m pytest tests/

# Restart the service
sudo systemctl start delta-bot

# Check status
sudo systemctl status delta-bot
```

## Troubleshooting

### Bot Won't Start

```bash
# Check service status
sudo systemctl status delta-bot

# View recent logs
journalctl -u delta-bot -n 50

# Check Python errors
python -m bot.main config.local.json
```

### Out of Memory Issues

```bash
# Check memory usage
free -h

# Add swap space (2GB)
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Make swap permanent
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### Network Issues

```bash
# Test RPC connectivity
curl -X POST https://mainnet.infura.io/v3/YOUR_KEY \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'

# Test Hyperliquid API
curl https://api.hyperliquid.xyz/info

# Check DNS resolution
nslookup api.hyperliquid.xyz
```

## Resource Monitoring

```bash
# Install monitoring tools
sudo apt install -y htop iotop nethogs

# Monitor CPU and memory
htop

# Monitor disk I/O
sudo iotop

# Monitor network usage
sudo nethogs

# Check disk space
df -h
```

## Cost Optimization

### AWS t3.small Estimated Monthly Cost
- **Instance**: ~$15/month (us-east-1)
- **Storage (20 GB)**: ~$2/month
- **Data Transfer**: Variable (typically < $5/month)
- **Total**: ~$22-25/month

### Reduce Costs
```bash
# Stop instance when not needed (development/testing)
# On AWS Console or CLI:
aws ec2 stop-instances --instance-ids i-1234567890abcdef0

# Use AWS Free Tier eligible instance types for testing
# t2.micro (1 vCPU, 1 GB RAM) - Free tier eligible
```

## Production Checklist

- [ ] Update all packages: `sudo apt update && sudo apt upgrade -y`
- [ ] Configure `.env` with real credentials
- [ ] Set proper file permissions: `chmod 600 .env`
- [ ] Enable firewall: `sudo ufw enable`
- [ ] Set up systemd service
- [ ] Configure log rotation
- [ ] Set up automated backups
- [ ] Test bot with small positions first
- [ ] Set up health checks
- [ ] Configure monitoring and alerts
- [ ] Document recovery procedures
- [ ] Keep backup of private keys offline

## Support

For issues specific to AWS deployment:
- AWS Support: https://aws.amazon.com/support/
- Ubuntu Documentation: https://help.ubuntu.com/

For bot-specific issues:
- GitHub Issues: https://github.com/TomV77/uniswap-v3-delta-neutral-bot/issues
- README: See main README.md for bot configuration and usage
