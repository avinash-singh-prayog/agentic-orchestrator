# SLIM Transporter - EC2 Direct Deployment

Simple deployment of SLIM Transporter directly on EC2 using Docker Compose.

## Prerequisites

- EC2 instance with Docker and Docker Compose installed
- Security Group allowing inbound TCP on port 46357

## Quick Start

```bash
# 1. Copy this directory to your EC2 instance
scp -r config/docker/slim-ec2 ec2-user@<EC2_IP>:~/slim-transporter

# 2. SSH into EC2
ssh ec2-user@<EC2_IP>

# 3. Start SLIM
cd ~/slim-transporter
chmod +x deploy.sh
./deploy.sh start
```

## Commands

| Command | Description |
|---------|-------------|
| `./deploy.sh start` | Start SLIM Transporter |
| `./deploy.sh stop` | Stop SLIM Transporter |
| `./deploy.sh restart` | Restart SLIM Transporter |
| `./deploy.sh status` | Check status and health |
| `./deploy.sh logs` | View container logs |
| `./deploy.sh update` | Pull latest image and restart |

## Ports

| Port | Purpose |
|------|---------|
| 46357 | Transport + Health (`/health`) |

## Configuration

Edit `slim.yaml` to customize SLIM settings. After changes:
```bash
./deploy.sh restart
```

## Logs

View logs:
```bash
./deploy.sh logs
```

Or directly:
```bash
docker logs -f slim-transporter
```

## Health Check

```bash
curl http://localhost:46357/health
```

## Auto-Start on Boot

To ensure SLIM starts automatically after EC2 reboot:

```bash
# Add to crontab
(crontab -l 2>/dev/null; echo "@reboot cd ~/slim-transporter && ./deploy.sh start") | crontab -
```

Or create a systemd service (see `slim-transporter.service` file).
