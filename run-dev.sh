#!/bin/bash

# Development Runner Script
# Runs all services in development mode with auto-reload

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting Development Services with Auto-Reload${NC}\n"

# Check if required tools are installed
command -v node >/dev/null 2>&1 || { echo "❌ Node.js is required but not installed. Aborting." >&2; exit 1; }
command -v uv >/dev/null 2>&1 || { echo "❌ uv is required. Install with: pip install uv" >&2; exit 1; }

# Load environment variables if Pinelabs.env exists
if [ -f "Pinelabs.env" ]; then
    echo -e "${YELLOW}📝 Loading environment variables from Pinelabs.env${NC}"
    # Export variables line by line (more reliable than xargs)
    while IFS= read -r line || [ -n "$line" ]; do
        # Skip comments and empty lines
        [[ "$line" =~ ^[[:space:]]*# ]] && continue
        [[ -z "${line// }" ]] && continue
        # Export the variable
        export "$line" 2>/dev/null || true
    done < Pinelabs.env
fi

# Ensure VITE_ORCHESTRATOR_API_URL is set (required for frontend)
if [ -z "$VITE_ORCHESTRATOR_API_URL" ]; then
    export VITE_ORCHESTRATOR_API_URL=http://localhost:3044
    echo -e "${YELLOW}📝 Set VITE_ORCHESTRATOR_API_URL=http://localhost:3044${NC}"
fi

# Function to kill process on port if in use
kill_port() {
    local port=$1
    local pids=$(lsof -ti :$port 2>/dev/null)
    if [ ! -z "$pids" ]; then
        echo -e "${YELLOW}⚠️  Port $port is in use. Killing process(es)...${NC}"
        echo "$pids" | xargs kill -9 2>/dev/null || true
        sleep 1
        echo -e "${GREEN}   ✓ Port $port freed${NC}"
    fi
}

# Check and kill processes on ports
echo -e "${BLUE}🔍 Checking and freeing ports...${NC}"
kill_port 3000
kill_port 3044

# Function to setup Python service
setup_python_service() {
    local service_path=$1
    local service_name=$2
    
    echo -e "${BLUE}📦 Setting up $service_name...${NC}"
    cd "$service_path"
    
    if [ ! -d ".venv" ]; then
        echo -e "${YELLOW}   Creating virtual environment...${NC}"
        uv venv
    fi
    
    # Ensure dependencies are installed (uv pip install is idempotent)
    if [ -d ".venv" ]; then
        echo -e "${YELLOW}   Installing/updating dependencies...${NC}"
        # Use uv directly with the venv
        uv pip install -e . --python .venv/bin/python 2>&1 | grep -v "already satisfied" || true
    fi
    
    cd - > /dev/null
}

# Setup Python services
echo -e "\n${BLUE}📦 Setting up Python services...${NC}"
setup_python_service "src/orchestrator/supervisor_agent" "Supervisor Agent"

# Setup Frontend
echo -e "\n${BLUE}📦 Setting up Frontend...${NC}"
cd src/frontend
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}   Installing npm dependencies...${NC}"
    npm install
fi
cd - > /dev/null

# Function to run service in background
run_service() {
    local name=$1
    local cmd=$2
    local dir=$3
    
    echo -e "${GREEN}▶️  Starting $name...${NC}"
    (
        cd "$dir"
        eval "$cmd"
    ) 2>&1 | sed "s/^/[$name] /" &
    echo $! > "/tmp/${name}.pid"
    echo -e "${GREEN}   ✓ $name started (PID: $(cat /tmp/${name}.pid))${NC}"
}

# Clean up function
cleanup() {
    echo -e "\n${YELLOW}🛑 Stopping all services...${NC}"
    for pidfile in /tmp/*.pid; do
        if [ -f "$pidfile" ]; then
            pid=$(cat "$pidfile")
            service=$(basename "$pidfile" .pid)
            if kill -0 "$pid" 2>/dev/null; then
                kill "$pid" 2>/dev/null || true
                echo -e "${GREEN}   ✓ Stopped $service${NC}"
            fi
            rm -f "$pidfile"
        fi
    done
    exit 0
}

# Trap Ctrl+C
trap cleanup INT TERM

# Start services
echo -e "\n${BLUE}🚀 Starting services...${NC}\n"

# Frontend
run_service "frontend" "npm run dev" "src/frontend"

# Supervisor Agent
run_service "supervisor-agent" ".venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 3044 --reload" "src/orchestrator/supervisor_agent"

echo -e "\n${GREEN}✅ All services started!${NC}\n"
echo -e "${BLUE}📍 Services running at:${NC}"
echo -e "   Frontend:           http://localhost:3000"
echo -e "   Supervisor Agent:   http://localhost:3044"
echo -e "${YELLOW}🛑 Press Ctrl+C to stop all services${NC}\n"

# Wait for all background processes
wait
