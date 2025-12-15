# Docker Deployment Guide

This guide provides instructions for deploying the Delta-Neutral Hedging Bot using Docker and Docker Compose. Docker provides better isolation and eliminates many configuration issues compared to traditional systemd deployments.

## Why Docker?

**Advantages of Docker deployment:**
- ✅ Isolated environment with all dependencies included
- ✅ Consistent behavior across different systems (local, AWS, etc.)
- ✅ No Python version conflicts or system package issues
- ✅ Easy to update, restart, and manage
- ✅ Better resource management and monitoring
- ✅ Eliminates "works on my machine" problems
- ✅ Simplified deployment process

## Prerequisites

### Install Docker and Docker Compose

**On Ubuntu/Debian:**
```bash
# Update package index
sudo apt update

# Install prerequisites
sudo apt install -y ca-certificates curl gnupg lsb-release

# Add Docker's official GPG key
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Set up the repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Verify installation
docker --version
docker compose version
```

**Add your user to the docker group (optional - allows running without sudo):**
```bash
sudo usermod -aG docker $USER
# Log out and back in for this to take effect
```

## Quick Start - Docker Compose (Recommended)

### 1. Clone Repository and Configure

```bash
# Clone the repository
cd ~
git clone https://github.com/TomV77/uniswap-v3-delta-neutral-bot.git
cd uniswap-v3-delta-neutral-bot

# Copy and configure environment file
cp .env.example .env
nano .env  # Fill in your credentials
```

### 2. Create Logs Directory

```bash
# Create logs directory for persistence
mkdir -p logs
```

### 3. Build and Start the Bot

```bash
# Build the Docker image
docker compose build

# Start the bot in detached mode
docker compose up -d

# View logs
docker compose logs -f
```

That's it! The bot is now running in a Docker container.

## Docker Compose Commands

### Start the Bot
```bash
docker compose up -d
```

### Stop the Bot
```bash
docker compose down
```

### View Live Logs
```bash
docker compose logs -f
```

### View Last N Lines of Logs
```bash
docker compose logs --tail=100
```

### Restart the Bot
```bash
docker compose restart
```

### Rebuild After Code Changes
```bash
docker compose down
docker compose build --no-cache
docker compose up -d
```

### Check Status
```bash
docker compose ps
```

### Execute Commands Inside Container
```bash
docker compose exec delta-bot python -c "from bot.main import DeltaNeutralBot; print('OK')"
```

## Manual Docker Commands (Advanced)

If you prefer to use Docker directly without Docker Compose:

### Build Image
```bash
docker build -t delta-neutral-bot:latest .
```

### Run Container
```bash
docker run -d \
  --name delta-neutral-bot \
  --restart unless-stopped \
  --env-file .env \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/.env:/app/.env:ro \
  delta-neutral-bot:latest
```

### View Logs
```bash
docker logs -f delta-neutral-bot
```

### Stop Container
```bash
docker stop delta-neutral-bot
```

### Start Container
```bash
docker start delta-neutral-bot
```

### Remove Container
```bash
docker rm -f delta-neutral-bot
```

## AWS Deployment with Docker

### Option 1: Docker Compose on EC2

On your AWS EC2 instance (t3.small or larger):

```bash
# Install Docker (see prerequisites above)
sudo apt update
sudo apt install -y docker.io docker-compose

# Clone and configure
cd ~
git clone https://github.com/TomV77/uniswap-v3-delta-neutral-bot.git
cd uniswap-v3-delta-neutral-bot
cp .env.example .env
nano .env  # Configure your settings

# Create logs directory
mkdir -p logs

# Set proper permissions
chmod 600 .env

# Build and start
docker compose build
docker compose up -d

# Check status
docker compose ps
docker compose logs --tail=50
```

### Option 2: Docker with Systemd (Auto-start on Boot)

Create a systemd service that manages Docker Compose:

```bash
sudo tee /etc/systemd/system/delta-bot-docker.service > /dev/null <<EOF
[Unit]
Description=Delta-Neutral Bot Docker Service
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$HOME/uniswap-v3-delta-neutral-bot
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
sudo systemctl daemon-reload

# Enable service
sudo systemctl enable delta-bot-docker

# Start service
sudo systemctl start delta-bot-docker

# Check status
sudo systemctl status delta-bot-docker
```

## Monitoring and Maintenance

### View Resource Usage
```bash
# Real-time resource usage
docker stats delta-neutral-bot

# Or with docker compose
docker compose stats
```

### Access Container Shell
```bash
docker compose exec delta-bot bash
# Or if bash is not available
docker compose exec delta-bot sh
```

### Inspect Container
```bash
docker compose inspect delta-bot
```

### View Container Details
```bash
docker compose ps
docker inspect delta-neutral-bot
```

## Updating the Bot

### Method 1: Docker Compose (Recommended)

```bash
cd ~/uniswap-v3-delta-neutral-bot

# Backup configuration
cp .env .env.backup.$(date +%Y%m%d_%H%M%S)

# Stop the bot
docker compose down

# Pull latest changes
git pull origin main

# Rebuild image
docker compose build --no-cache

# Start the bot
docker compose up -d

# Monitor logs
docker compose logs -f
```

### Method 2: Automated Update Script

Create an update script:

```bash
cat > ~/update-docker-bot.sh <<'EOF'
#!/bin/bash
set -e

echo "=== Updating Delta-Neutral Bot (Docker) ==="

BOT_DIR="$HOME/uniswap-v3-delta-neutral-bot"
BACKUP_DIR="$HOME/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup configuration
echo "Backing up configuration..."
cp $BOT_DIR/.env $BACKUP_DIR/env_backup_$DATE

# Navigate to bot directory
cd $BOT_DIR

# Stop container
echo "Stopping bot container..."
docker compose down

# Pull updates
echo "Pulling latest changes..."
git pull origin main

# Rebuild image
echo "Rebuilding Docker image..."
docker compose build --no-cache

# Start container
echo "Starting bot container..."
docker compose up -d

# Wait for container to start
sleep 5

# Check status
if docker compose ps | grep -q "Up"; then
    echo "✓ Bot updated and running successfully!"
    docker compose logs --tail=20
else
    echo "✗ Bot failed to start after update!"
    echo "Check logs: docker compose logs"
    exit 1
fi

echo "Update completed at $(date)"
EOF

chmod +x ~/update-docker-bot.sh
```

Run the update:
```bash
~/update-docker-bot.sh
```

## Troubleshooting

### Bot Container Won't Start

```bash
# Check container status
docker compose ps

# View error logs
docker compose logs

# Try starting in foreground to see errors
docker compose up

# Check if port conflicts exist
docker compose down
docker compose up -d
```

### Connection Issues

```bash
# Test network connectivity from inside container
docker compose exec delta-bot ping -c 3 8.8.8.8

# Test RPC endpoint
docker compose exec delta-bot python -c "from web3 import Web3; w3 = Web3(Web3.HTTPProvider('YOUR_RPC_URL')); print(w3.is_connected())"
```

### Out of Disk Space

```bash
# Remove unused Docker images and containers
docker system prune -a

# Remove all stopped containers
docker container prune

# Remove unused images
docker image prune -a

# Check disk usage
df -h
docker system df
```

### Container Keeps Restarting

```bash
# View container logs
docker compose logs --tail=100

# Check resource limits
docker compose config

# Inspect container
docker inspect delta-neutral-bot
```

### Permission Issues

```bash
# Fix log directory permissions
sudo chown -R $USER:$USER logs/

# Fix .env permissions
chmod 600 .env

# Ensure Docker has proper permissions
sudo usermod -aG docker $USER
# Log out and back in
```

## Security Best Practices

### 1. Secure Environment File
```bash
# Ensure .env is not world-readable
chmod 600 .env

# Verify permissions
ls -la .env  # Should show: -rw------- 1 username username
```

### 2. Use Docker Secrets (Production)

For production deployments, consider using Docker secrets:

```bash
# Create secrets
echo "your-private-key" | docker secret create hyperliquid_key -
echo "your-rpc-url" | docker secret create rpc_url -

# Update docker-compose.yml to use secrets
# (requires Docker Swarm mode)
```

### 3. Network Isolation

The default docker-compose.yml uses bridge networking. For additional security:
- Use custom networks
- Implement firewall rules
- Consider using Docker Swarm or Kubernetes for production

### 4. Regular Updates

```bash
# Update Docker itself
sudo apt update
sudo apt upgrade docker-ce docker-ce-cli containerd.io

# Regularly rebuild bot image to get security updates
docker compose build --no-cache
```

## Resource Management

### Adjust Resource Limits

Edit `docker-compose.yml` to modify resource limits:

```yaml
deploy:
  resources:
    limits:
      cpus: '2.0'      # Increase CPU limit
      memory: 1G       # Increase memory limit
    reservations:
      cpus: '1.0'
      memory: 512M
```

### Monitor Resource Usage Over Time

```bash
# Create monitoring script
cat > ~/monitor-bot.sh <<'EOF'
#!/bin/bash
while true; do
    echo "=== $(date) ==="
    docker stats delta-neutral-bot --no-stream
    sleep 60
done
EOF

chmod +x ~/monitor-bot.sh

# Run in background
nohup ~/monitor-bot.sh >> ~/bot-monitoring.log 2>&1 &
```

## Log Management

### Log Rotation

Docker automatically handles log rotation if configured in docker-compose.yml:

```yaml
logging:
  driver: json-file
  options:
    max-size: "10m"    # Maximum log file size
    max-file: "3"      # Keep last 3 log files
```

### View Different Log Types

```bash
# Application logs
docker compose logs delta-bot

# Docker daemon logs
sudo journalctl -u docker

# Container logs from Docker directory
sudo ls -lh /var/lib/docker/containers/
```

## Backup and Recovery

### Backup Configuration

```bash
# Create backup
tar -czf delta-bot-backup-$(date +%Y%m%d).tar.gz \
    .env \
    config.json \
    logs/

# Restore from backup
tar -xzf delta-bot-backup-20240101.tar.gz
```

### Export/Import Docker Image

```bash
# Export image
docker save delta-neutral-bot:latest | gzip > delta-bot-image.tar.gz

# Import on another system
gunzip -c delta-bot-image.tar.gz | docker load
```

## Comparison: Docker vs Systemd

| Feature | Docker | Systemd |
|---------|--------|---------|
| Setup Complexity | Low | Medium |
| Isolation | Excellent | Good |
| Portability | Excellent | Limited |
| Resource Management | Built-in | Manual |
| Updates | Simple rebuild | Manual dependency management |
| Debugging | Easy logs access | Log files |
| Dependencies | Bundled | System-wide |
| Recommended For | All users | Advanced users |

**Recommendation:** Use Docker for most deployments due to better isolation, easier management, and fewer configuration issues.

## Best Practices

1. **Always use docker-compose** for easier management
2. **Mount .env as read-only** (`:ro`) for security
3. **Use named volumes** for persistent data
4. **Set resource limits** to prevent resource exhaustion
5. **Enable health checks** for automatic restart
6. **Keep images up to date** with regular rebuilds
7. **Monitor logs** regularly
8. **Backup configuration** before updates
9. **Test updates** in development first
10. **Use specific image tags** in production (not `latest`)

## Support

For Docker-related issues:
- Docker Documentation: https://docs.docker.com/
- Docker Compose: https://docs.docker.com/compose/

For bot-specific issues:
- GitHub Issues: https://github.com/TomV77/uniswap-v3-delta-neutral-bot/issues
- README: See main README.md for bot configuration

---

**Note:** Docker deployment is the recommended method for production use due to better isolation, consistency, and easier management compared to traditional systemd services.
