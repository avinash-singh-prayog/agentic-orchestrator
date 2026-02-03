#!/bin/bash

# Manual Deployment Script for Agentic Orchestrator
# This script replaces Jenkins deployment when Jenkins is down
# 
# Usage:
#   ./manual-deploy.sh [service]
#   service options: supervisor, rca, frontend, or all (default: all)

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# AWS Configuration
AWS_ACCOUNT_ID='084375559937'
AWS_REGION='ap-south-1'
ECR_BASE="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

# ECS Configuration
CLUSTER_NAME='prayog-prod-ecs'

# Service-specific configurations
SUPERVISOR_REPO='prayog-prod-agentic-orchestrator/pinelabs-supervisor-agent'
SUPERVISOR_SERVICE='prayog-ag-orch-prod-pinelabs-supervisor-agent'
SUPERVISOR_TASK_DEF='prayog-prod-ecs-ag-orch-pinelabs-supervisor-agent-td'
SUPERVISOR_PORT=3044

RCA_REPO='prayog-prod-agentic-orchestrator/transaction-rca-agent'
RCA_SERVICE='prayog-ag-orch-prod-transaction-rca-agent'
RCA_TASK_DEF='prayog-prod-ecs-ag-orch-transaction-rca-agent-td'
RCA_PORT=3045
SLIM_ENDPOINT='http://3.7.70.176:46357'

# Frontend Configuration
S3_BUCKET='pinelabs-frontend'
CLOUDFRONT_ID='E29AQVB9X1DUQS'
VITE_ORCHESTRATOR_API_URL='https://prod-apis.prayog.io'

# Get service to deploy (default: all)
SERVICE=${1:-all}

# Generate a build number (timestamp-based)
BUILD_NUMBER=$(date +%Y%m%d%H%M%S)

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Manual Deployment Script${NC}"
echo -e "${BLUE}Build Number: ${BUILD_NUMBER}${NC}"
echo -e "${BLUE}Service: ${SERVICE}${NC}"
echo -e "${BLUE}========================================${NC}"

# Check prerequisites
check_prerequisites() {
    echo -e "${YELLOW}Checking prerequisites...${NC}"
    
    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        echo -e "${RED}❌ AWS CLI is not installed. Please install it first.${NC}"
        exit 1
    fi
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}❌ Docker is not installed. Please install it first.${NC}"
        exit 1
    fi
    
    # Check jq
    if ! command -v jq &> /dev/null; then
        echo -e "${RED}❌ jq is not installed. Please install it: brew install jq${NC}"
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        echo -e "${RED}❌ AWS credentials not configured. Please run 'aws configure'${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ All prerequisites met${NC}"
}

# Login to ECR
login_ecr() {
    echo -e "${YELLOW}Logging into ECR...${NC}"
    aws ecr get-login-password --region ${AWS_REGION} | \
        docker login --username AWS --password-stdin ${ECR_BASE}
    echo -e "${GREEN}✅ ECR login successful${NC}"
}

# Deploy Supervisor Agent
deploy_supervisor() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}Deploying Supervisor Agent${NC}"
    echo -e "${BLUE}========================================${NC}"
    
    IMAGE_URI="${ECR_BASE}/${SUPERVISOR_REPO}"
    
    # Build Docker image
    echo -e "${YELLOW}Building Docker image...${NC}"
    cd src/orchestrator/supervisor_agent
    docker build \
        -t ${IMAGE_URI}:${BUILD_NUMBER} \
        -t ${IMAGE_URI}:latest .
    
    # Push to ECR
    echo -e "${YELLOW}Pushing Docker images to ECR...${NC}"
    docker push ${IMAGE_URI}:${BUILD_NUMBER}
    docker push ${IMAGE_URI}:latest
    
    # Get current task definition
    echo -e "${YELLOW}Fetching current task definition...${NC}"
    aws ecs describe-task-definition \
        --task-definition ${SUPERVISOR_TASK_DEF} \
        --query 'taskDefinition' > /tmp/task-def-supervisor.json
    
    # Update task definition with new image
    echo -e "${YELLOW}Updating task definition...${NC}"
    cat /tmp/task-def-supervisor.json | jq --arg IMAGE "${IMAGE_URI}:${BUILD_NUMBER}" '
        .containerDefinitions[0].image = $IMAGE |
        .containerDefinitions[0].portMappings[0].containerPort = 3044 |
        .containerDefinitions[0].portMappings[0].hostPort = 3044 |
        .containerDefinitions[0].healthCheck = {
            "command": ["CMD-SHELL", "curl -f http://localhost:3044/supervisor-pinelabs/health || exit 1"],
            "interval": 30,
            "timeout": 5,
            "retries": 3,
            "startPeriod": 60
        } |
        del(
            .taskDefinitionArn,
            .revision,
            .status,
            .requiresAttributes,
            .compatibilities,
            .registeredAt,
            .registeredBy
        )
    ' > /tmp/new-task-def-supervisor.json
    
    # Register new task definition
    echo -e "${YELLOW}Registering new task definition...${NC}"
    NEW_TASK_DEF_ARN=$(aws ecs register-task-definition \
        --cli-input-json file:///tmp/new-task-def-supervisor.json \
        --query 'taskDefinition.taskDefinitionArn' \
        --output text)
    
    echo -e "${GREEN}New task definition ARN: ${NEW_TASK_DEF_ARN}${NC}"
    
    # Update ECS service
    echo -e "${YELLOW}Updating ECS service...${NC}"
    aws ecs update-service \
        --cluster ${CLUSTER_NAME} \
        --service ${SUPERVISOR_SERVICE} \
        --task-definition ${NEW_TASK_DEF_ARN} \
        --force-new-deployment \
        --region ${AWS_REGION}
    
    # Cleanup
    rm -f /tmp/task-def-supervisor.json /tmp/new-task-def-supervisor.json
    
    # Clean up local Docker images
    docker rmi ${IMAGE_URI}:${BUILD_NUMBER} ${IMAGE_URI}:latest || true
    
    cd - > /dev/null
    echo -e "${GREEN}✅ Supervisor Agent deployment triggered successfully!${NC}"
}

# Deploy RCA Agent
deploy_rca() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}Deploying Transaction RCA Agent${NC}"
    echo -e "${BLUE}========================================${NC}"
    
    IMAGE_URI="${ECR_BASE}/${RCA_REPO}"
    
    # Build Docker image
    echo -e "${YELLOW}Building Docker image...${NC}"
    cd src/orchestrator/transaction_rca_agent
    docker build \
        -t ${IMAGE_URI}:${BUILD_NUMBER} \
        -t ${IMAGE_URI}:latest .
    
    # Push to ECR
    echo -e "${YELLOW}Pushing Docker images to ECR...${NC}"
    docker push ${IMAGE_URI}:${BUILD_NUMBER}
    docker push ${IMAGE_URI}:latest
    
    # Get current task definition
    echo -e "${YELLOW}Fetching current task definition...${NC}"
    aws ecs describe-task-definition \
        --task-definition ${RCA_TASK_DEF} \
        --query 'taskDefinition' > /tmp/task-def-rca.json
    
    # Update task definition with new image and SLIM_ENDPOINT
    echo -e "${YELLOW}Updating task definition...${NC}"
    cat /tmp/task-def-rca.json | jq --arg IMAGE "${IMAGE_URI}:${BUILD_NUMBER}" \
                                     --arg SLIM_ENDPOINT "${SLIM_ENDPOINT}" '
        .containerDefinitions[0].image = $IMAGE |
        .containerDefinitions[0].portMappings[0].containerPort = 3045 |
        .containerDefinitions[0].portMappings[0].hostPort = 3045 |
        .containerDefinitions[0].environment = (
            (.containerDefinitions[0].environment // []) |
            map(select(.name != "SLIM_ENDPOINT")) +
            [{"name":"SLIM_ENDPOINT","value":$SLIM_ENDPOINT}]
        ) |
        .containerDefinitions[0].healthCheck = {
            "command": ["CMD-SHELL", "curl -f http://localhost:3045/rca-pinelabs/health || exit 1"],
            "interval": 30,
            "timeout": 5,
            "retries": 3,
            "startPeriod": 60
        } |
        del(
            .taskDefinitionArn,
            .revision,
            .status,
            .requiresAttributes,
            .compatibilities,
            .registeredAt,
            .registeredBy
        )
    ' > /tmp/new-task-def-rca.json
    
    # Register new task definition
    echo -e "${YELLOW}Registering new task definition...${NC}"
    NEW_TASK_DEF_ARN=$(aws ecs register-task-definition \
        --cli-input-json file:///tmp/new-task-def-rca.json \
        --query 'taskDefinition.taskDefinitionArn' \
        --output text)
    
    echo -e "${GREEN}New task definition ARN: ${NEW_TASK_DEF_ARN}${NC}"
    
    # Update ECS service
    echo -e "${YELLOW}Updating ECS service...${NC}"
    aws ecs update-service \
        --cluster ${CLUSTER_NAME} \
        --service ${RCA_SERVICE} \
        --task-definition ${NEW_TASK_DEF_ARN} \
        --force-new-deployment \
        --region ${AWS_REGION}
    
    # Cleanup
    rm -f /tmp/task-def-rca.json /tmp/new-task-def-rca.json
    
    # Clean up local Docker images
    docker rmi ${IMAGE_URI}:${BUILD_NUMBER} ${IMAGE_URI}:latest || true
    
    cd - > /dev/null
    echo -e "${GREEN}✅ Transaction RCA Agent deployment triggered successfully!${NC}"
}

# Deploy Frontend
deploy_frontend() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}Deploying Frontend${NC}"
    echo -e "${BLUE}========================================${NC}"
    
    # Check if VITE_ORCHESTRATOR_API_URL is set
    if [ -z "${VITE_ORCHESTRATOR_API_URL}" ]; then
        echo -e "${YELLOW}VITE_ORCHESTRATOR_API_URL not set, using default: https://prod-apis.prayog.io${NC}"
        export VITE_ORCHESTRATOR_API_URL='https://prod-apis.prayog.io'
    fi
    
    echo -e "${YELLOW}Building with VITE_ORCHESTRATOR_API_URL=${VITE_ORCHESTRATOR_API_URL}${NC}"
    
    # Build frontend
    echo -e "${YELLOW}Building frontend...${NC}"
    cd src/frontend
    
    # Check Node.js
    if ! command -v node &> /dev/null; then
        echo -e "${RED}❌ Node.js is not installed. Please install Node.js 18 or higher.${NC}"
        exit 1
    fi
    
    # Install dependencies and build
    npm install
    npm run build
    
    # Deploy to S3
    echo -e "${YELLOW}Deploying to S3...${NC}"
    aws s3 sync dist/ s3://${S3_BUCKET} --delete --region ${AWS_REGION}
    
    # Invalidate CloudFront cache
    echo -e "${YELLOW}Invalidating CloudFront cache...${NC}"
    aws cloudfront create-invalidation \
        --distribution-id ${CLOUDFRONT_ID} \
        --paths "/*" \
        --region ${AWS_REGION}
    
    cd - > /dev/null
    echo -e "${GREEN}✅ Frontend deployment completed successfully!${NC}"
}

# Main execution
main() {
    check_prerequisites
    
    case ${SERVICE} in
        supervisor)
            login_ecr
            deploy_supervisor
            ;;
        rca)
            login_ecr
            deploy_rca
            ;;
        frontend)
            deploy_frontend
            ;;
        all)
            login_ecr
            deploy_supervisor
            deploy_rca
            deploy_frontend
            ;;
        *)
            echo -e "${RED}❌ Invalid service: ${SERVICE}${NC}"
            echo -e "Usage: ./manual-deploy.sh [supervisor|rca|frontend|all]"
            exit 1
            ;;
    esac
    
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}Deployment completed!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo -e "${YELLOW}Note: ECS deployments may take a few minutes to complete.${NC}"
    echo -e "${YELLOW}Monitor your ECS services in the AWS Console.${NC}"
}

# Run main function
main
