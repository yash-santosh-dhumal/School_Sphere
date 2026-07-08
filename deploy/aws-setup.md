# EduPulse — AWS Deployment Guide

This guide walks through deploying EduPulse on AWS using EC2 + Docker Compose.

---

## Architecture Overview

```
                    ┌─────────────┐
                    │   Internet  │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  Elastic IP │
                    └──────┬──────┘
                           │
              ┌────────────▼────────────┐
              │    EC2 Instance         │
              │    (t2.micro)           │
              │                         │
              │  ┌───────────────────┐  │
              │  │    Nginx :80/443  │  │
              │  └────────┬──────────┘  │
              │           │             │
              │  ┌────────▼──────────┐  │
              │  │  FastAPI :8000    │  │
              │  └────────┬──────────┘  │
              │           │             │
              │  ┌────────┴──────────┐  │
              │  │                   │  │
              │  ▼                   ▼  │
              │ MySQL:3306     Redis:6379│
              │                         │
              │ Celery Worker           │
              │                         │
              └─────────────────────────┘
```

---

## Prerequisites

- An AWS account (free tier eligible)
- A terminal with SSH access
- Docker and Docker Compose on the EC2 instance

---

## Step 1: Launch an EC2 Instance

1. Go to **AWS Console → EC2 → Launch Instance**
2. Configure:
   - **Name**: `edupulse-server`
   - **AMI**: Ubuntu Server 24.04 LTS (free tier eligible)
   - **Instance type**: `t2.micro` (free tier)
   - **Key pair**: Create or select an existing key pair (download the `.pem` file)
   - **Network**: Default VPC
   - **Storage**: 20 GB gp3 (free tier allows up to 30 GB)

3. **Security Group** — create one named `edupulse-sg` with these rules:

| Type  | Port | Source        | Description        |
|-------|------|--------------|--------------------|
| SSH   | 22   | Your IP      | SSH access         |
| HTTP  | 80   | 0.0.0.0/0    | Web traffic        |
| HTTPS | 443  | 0.0.0.0/0    | Secure web traffic |

4. Click **Launch Instance**

---

## Step 2: Allocate an Elastic IP

1. Go to **EC2 → Elastic IPs → Allocate Elastic IP address**
2. Associate it with your `edupulse-server` instance
3. Note the Elastic IP — this is your server's permanent public IP

---

## Step 3: SSH into the Instance

```bash
# Make key read-only
chmod 400 ~/path-to/edupulse-key.pem

# Connect
ssh -i ~/path-to/edupulse-key.pem ubuntu@<ELASTIC_IP>
```

---

## Step 4: Install Docker & Docker Compose

Run on the EC2 instance:

```bash
# Update packages
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group (no sudo needed)
sudo usermod -aG docker $USER

# Install Docker Compose plugin
sudo apt install -y docker-compose-plugin

# Apply group changes
newgrp docker

# Verify
docker --version
docker compose version
```

---

## Step 5: Clone the Repository

```bash
cd ~
git clone https://github.com/yash-santosh-dhumal/EduPulse.git
cd EduPulse
```

---

## Step 6: Configure Environment

```bash
# Create production .env from the template
cp .env.production.example .env

# Edit with your production values
nano .env
```

**Critical values to change**:
- `JWT_SECRET_KEY` — Generate: `openssl rand -hex 32`
- `MYSQL_ROOT_PASSWORD` — Use a strong password
- `MYSQL_PASSWORD` — Use a strong password
- `CORS_ORIGINS` — Set to your domain or Elastic IP

---

## Step 7: Deploy

```bash
# Build and start in production mode
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d

# Check all services are healthy
docker compose ps

# View logs
docker compose logs -f api

# Test the API
curl http://localhost/api/v1/health
```

---

## Step 8: Set Up SSL (Optional — requires domain)

If you have a domain pointed to your Elastic IP:

```bash
# Install certbot
sudo apt install -y certbot

# Get certificate (stop nginx first)
docker compose stop nginx
sudo certbot certonly --standalone -d yourdomain.com

# Copy certs to nginx volume
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem nginx/ssl/
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem nginx/ssl/

# Uncomment the HTTPS blocks in nginx/nginx.conf
# Then restart
docker compose up -d nginx
```

---

## Step 9: Set Up Monitoring (Optional)

```bash
# Start monitoring stack
docker compose -f docker-compose.monitoring.yml up -d

# Access Grafana at http://<ELASTIC_IP>:3000
# Default credentials: admin / admin
```

---

## Maintenance Commands

```bash
# View running services
docker compose ps

# View logs for a service
docker compose logs -f api
docker compose logs -f worker

# Restart a service
docker compose restart api

# Pull latest code and redeploy
git pull origin main
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d

# Run a manual backup
bash scripts/backup.sh

# Run database migrations manually
docker compose exec api python -m alembic upgrade head

# Open a shell in the API container
docker compose exec api /bin/bash

# Stop everything
docker compose down

# Stop and remove all data (⚠️ destructive)
docker compose down -v
```

---

## Cost Estimate (AWS Free Tier)

| Service              | Free Tier          | After Free Tier     |
|---------------------|--------------------|---------------------|
| EC2 t2.micro        | 750 hrs/mo (12 mo) | ~$8.50/mo           |
| EBS 20 GB gp3       | 30 GB free (12 mo) | ~$1.60/mo           |
| Elastic IP (in use) | Free               | Free                |
| Data Transfer       | 100 GB/mo          | $0.09/GB            |
| **Total (Free Tier)** | **$0/mo**       | **~$10/mo after**   |

> All services run inside Docker on a single EC2 instance, keeping costs minimal.
