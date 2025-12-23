#!/bin/bash
# SLIM Transporter - EC2 Deployment Script
# Usage: ./deploy.sh [start|stop|restart|status|logs|update]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check if Docker is installed
check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
}

# Use docker compose v2 if available, otherwise fall back to docker-compose
docker_compose_cmd() {
    if docker compose version &> /dev/null 2>&1; then
        docker compose "$@"
    else
        docker-compose "$@"
    fi
}

start() {
    log_info "Starting SLIM Transporter..."
    docker_compose_cmd up -d
    log_info "SLIM Transporter started successfully!"
    log_info "Transport port: 46357"
    status
}

stop() {
    log_info "Stopping SLIM Transporter..."
    docker_compose_cmd down
    log_info "SLIM Transporter stopped."
}

restart() {
    log_info "Restarting SLIM Transporter..."
    docker_compose_cmd restart
    log_info "SLIM Transporter restarted."
    status
}

status() {
    log_info "SLIM Transporter Status:"
    docker_compose_cmd ps
    echo ""
    log_info "Health Check:"
    if curl -sf http://localhost:46357/health > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓ Healthy${NC}"
    else
        echo -e "  ${RED}✗ Unhealthy or starting...${NC}"
    fi
}

logs() {
    docker_compose_cmd logs -f --tail=100
}

update() {
    log_info "Updating SLIM Transporter..."
    docker_compose_cmd pull
    docker_compose_cmd up -d
    log_info "SLIM Transporter updated!"
    status
}

# Main
check_docker

case "${1:-start}" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    status)
        status
        ;;
    logs)
        logs
        ;;
    update)
        update
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs|update}"
        exit 1
        ;;
esac
