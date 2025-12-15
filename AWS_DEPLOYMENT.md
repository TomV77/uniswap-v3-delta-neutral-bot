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

# Install Python 3.10 (default on Ubuntu 22.04) and required tools
sudo apt install -y python3 python3-venv python3-pip git curl

# Install system dependencies
sudo apt install -y build-essential libssl-dev libffi-dev python3-dev

# Verify Python version (should be 3.10.x)
python3 --version
```

**Optional - Install Python 3.11 or newer versions:**

If you specifically want Python 3.11 or newer (not required, but optional), you can install it from the deadsnakes PPA:

```bash
# Add deadsnakes PPA for newer Python versions
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update

# Install Python 3.11
sudo apt install -y python3.11 python3.11-venv python3.11-dev

# Verify installation
python3.11 --version

# Use python3.11 instead of python3 when creating the virtual environment:
# python3.11 -m venv venv
```

### 2. Clone Repository

```bash
# Clone the repository
cd ~
git clone https://github.com/TomV77/uniswap-v3-delta-neutral-bot.git
cd uniswap-v3-delta-neutral-bot

# Create virtual environment
python3 -m venv venv

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
# Note: Replace $USER with your actual username in the paths below
sudo tee /etc/systemd/system/delta-bot.service > /dev/null <<EOF
[Unit]
Description=Delta-Neutral Hedging Bot
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$HOME/uniswap-v3-delta-neutral-bot
Environment="PATH=$HOME/uniswap-v3-delta-neutral-bot/venv/bin"
ExecStart=$HOME/uniswap-v3-delta-neutral-bot/venv/bin/python -m bot.main config.local.json
Restart=always
RestartSec=10
StandardOutput=append:$HOME/uniswap-v3-delta-neutral-bot/bot.log
StandardError=append:$HOME/uniswap-v3-delta-neutral-bot/bot-error.log

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
ls -la .env  # Should show: -rw------- 1 username username
```

### SSH Key Authentication (Disable Password Login)

```bash
# On your local machine, generate SSH key if you don't have one
ssh-keygen -t ed25519 -C "your_email@example.com"

# Copy public key to server
ssh-copy-id -i ~/.ssh/id_ed25519.pub username@your-server-ip

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
$HOME/uniswap-v3-delta-neutral-bot/*.log {
    daily
    rotate 7
    compress
    delaycompress
    notifempty
    create 0644 $USER $USER
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
BACKUP_DIR="$HOME/backups"
mkdir -p $BACKUP_DIR

# Backup configuration files
tar -czf $BACKUP_DIR/config_backup_$DATE.tar.gz \
    $HOME/uniswap-v3-delta-neutral-bot/.env \
    $HOME/uniswap-v3-delta-neutral-bot/config.local.json

# Keep only last 7 days of backups
find $BACKUP_DIR -name "config_backup_*.tar.gz" -mtime +7 -delete

echo "Backup completed: config_backup_$DATE.tar.gz"
EOF

chmod +x ~/backup-config.sh

# Add to crontab (daily backup at 2 AM)
(crontab -l 2>/dev/null; echo "0 2 * * * $HOME/backup-config.sh") | crontab -
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
ERRORS=$(tail -n 100 $HOME/uniswap-v3-delta-neutral-bot/bot-error.log | grep -c "ERROR")
if [ $ERRORS -gt 10 ]; then
    echo "WARNING: $ERRORS errors found in recent logs"
fi

echo "Health check completed at $(date)"
EOF

chmod +x ~/check-bot-health.sh

# Run health check every 5 minutes
(crontab -l 2>/dev/null; echo "*/5 * * * * $HOME/check-bot-health.sh >> $HOME/health-check.log 2>&1") | crontab -
```

## Updating the Bot

When new commits are pushed to the repository, follow these steps to update your AWS deployment:

### Step 1: Stop the Bot Service

```bash
# Stop the running bot service
sudo systemctl stop delta-bot

# Verify it's stopped
sudo systemctl status delta-bot
```

### Step 2: Backup Current Configuration

```bash
# Navigate to bot directory
cd ~/uniswap-v3-delta-neutral-bot

# Backup your configuration files
cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
cp config.local.json config.local.json.backup.$(date +%Y%m%d_%H%M%S) 2>/dev/null || true

# Backup logs (optional)
cp bot.log bot.log.backup.$(date +%Y%m%d_%H%M%S) 2>/dev/null || true
cp bot-error.log bot-error.log.backup.$(date +%Y%m%d_%H%M%S) 2>/dev/null || true
```

### Step 3: Pull Latest Changes

```bash
# Ensure you're on the main branch
git checkout main

# Fetch and pull latest changes
git pull origin main

# If you have local changes that conflict, stash them first:
# git stash
# git pull origin main
# git stash pop
```

### Step 4: Update Dependencies (if needed)

```bash
# Activate virtual environment
source venv/bin/activate

# Update Python packages if requirements.txt changed
pip install --upgrade -r requirements.txt

# Verify installation
python -c "from bot.main import DeltaNeutralBot; print('Installation successful!')"
```

### Step 5: Review Configuration Changes

```bash
# Check if .env.example has new variables
diff .env.example .env.backup.* | grep "^<" || echo "No new environment variables"

# If new variables exist, add them to your .env file
nano .env

# Compare your config with any updates
# (Only if you use config.local.json)
diff config.json config.local.json.backup.* 2>/dev/null || true
```

### Step 6: Test the Update

```bash
# Run a quick test to ensure everything works
python -m bot.main --help 2>/dev/null || echo "Ready to start"

# Optional: Run the test suite if available
python -m pytest tests/ -v 2>/dev/null || echo "Tests not available or failed"
```

### Step 7: Restart the Bot Service

```bash
# Start the service
sudo systemctl start delta-bot

# Check status to ensure it's running
sudo systemctl status delta-bot

# Monitor logs for any errors
tail -f ~/uniswap-v3-delta-neutral-bot/bot.log
```

### Quick Update Command (One-liner)

For experienced users, here's a streamlined update command:

```bash
cd ~/uniswap-v3-delta-neutral-bot && \
sudo systemctl stop delta-bot && \
cp .env .env.backup && \
git pull origin main && \
source venv/bin/activate && \
pip install --upgrade -r requirements.txt && \
sudo systemctl start delta-bot && \
sudo systemctl status delta-bot
```

### Troubleshooting Updates

**If the bot won't start after update:**

```bash
# Check service status and logs
sudo systemctl status delta-bot
journalctl -u delta-bot -n 50

# Check Python errors directly
cd ~/uniswap-v3-delta-neutral-bot
source venv/bin/activate
python -m bot.main config.local.json
```

**If configuration conflicts occur:**

```bash
# Review what changed in .env.example
git diff HEAD~1 .env.example

# Update your .env with new required variables
nano .env
```

**If dependencies fail to install:**

```bash
# Recreate virtual environment
cd ~/uniswap-v3-delta-neutral-bot
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Rollback to Previous Version

If the update causes issues, you can rollback:

```bash
# Stop the service
sudo systemctl stop delta-bot

# View recent commits to find the version you want
git log --oneline -n 10

# Rollback to a specific commit (replace COMMIT_HASH)
git checkout COMMIT_HASH

# Or rollback to previous commit
git checkout HEAD~1

# Restore configuration backup
cp .env.backup.YYYYMMDD_HHMMSS .env

# Restart service
sudo systemctl start delta-bot
```

### Automated Update Script

Create an automated update script for convenience:

```bash
cat > ~/update-bot.sh <<'EOF'
#!/bin/bash

echo "=== Updating Delta-Neutral Bot ==="

# Configuration
BOT_DIR="$HOME/uniswap-v3-delta-neutral-bot"
BACKUP_DIR="$HOME/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p $BACKUP_DIR

# Stop service
echo "Stopping bot service..."
sudo systemctl stop delta-bot

# Backup configurations
echo "Backing up configuration..."
cp $BOT_DIR/.env $BACKUP_DIR/env_backup_$DATE
cp $BOT_DIR/config.local.json $BACKUP_DIR/config_backup_$DATE 2>/dev/null || true

# Pull updates
echo "Pulling latest changes..."
cd $BOT_DIR
git pull origin main

if [ $? -ne 0 ]; then
    echo "ERROR: Git pull failed!"
    echo "Restoring service..."
    sudo systemctl start delta-bot
    exit 1
fi

# Update dependencies
echo "Updating dependencies..."
source venv/bin/activate
pip install --upgrade -r requirements.txt

if [ $? -ne 0 ]; then
    echo "ERROR: Dependency update failed!"
    echo "Restoring service..."
    sudo systemctl start delta-bot
    exit 1
fi

# Restart service
echo "Restarting bot service..."
sudo systemctl start delta-bot

# Check status
sleep 2
if systemctl is-active --quiet delta-bot; then
    echo "✓ Bot updated and running successfully!"
    sudo systemctl status delta-bot
else
    echo "✗ Bot failed to start after update!"
    echo "Check logs: journalctl -u delta-bot -n 50"
    exit 1
fi

echo "Update completed at $(date)"
EOF

chmod +x ~/update-bot.sh

echo "Update script created at ~/update-bot.sh"
echo "Run it with: ~/update-bot.sh"
```

### Best Practices for Updates

1. **Always backup** your `.env` file before updating
2. **Review the changelog** or commit messages to understand what changed
3. **Test in development** environment first if possible
4. **Monitor logs** closely after updating
5. **Keep backups** for at least 7 days
6. **Update during low activity** periods to minimize disruption
7. **Have a rollback plan** ready before updating

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
