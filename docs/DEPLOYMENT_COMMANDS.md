# Deployment Commands Reference

## Local Development

### Using run-dev.sh (Recommended for development with auto-reload)
```bash
./run-dev.sh
```

### Using Docker Compose (For testing containerized setup)
```bash
# Load environment variables and start services
source Pinelabs.env && docker compose up --build

# Or run in detached mode
source Pinelabs.env && docker compose up --build -d

# Stop services
docker compose down

# View logs
docker compose logs -f

# View logs for specific service
docker compose logs -f supervisor-agent
```

## Jenkins Deployment

All Jenkins pipelines automatically handle:
1. ✅ Building Docker images
2. ✅ Pushing to ECR
3. ✅ Updating ECS task definitions
4. ✅ Deploying to ECS services
5. ✅ (Frontend) Deploying to S3 and invalidating CloudFront

### After Jenkins Build Completes

**No manual steps required!** The pipelines automatically:
- Push images to ECR repositories
- Update ECS task definitions with new image tags
- Trigger ECS service deployments with `--force-new-deployment`

### Optional: Monitor Deployments

You can verify deployments in AWS Console:
- **ECS**: Clusters → Check service status and running tasks
- **ECR**: Repositories → Verify new images with build numbers
- **CloudWatch**: Check logs if needed
- **S3** (Frontend): Verify new files in `pinelabs-frontend` bucket
- **CloudFront** (Frontend): Check invalidation status

### Jenkins Pipeline Details

#### Supervisor Agent
- **ECR Repo**: `084375559937.dkr.ecr.ap-south-1.amazonaws.com/prayog-prod-agentic-orchestrator/pinelabs-supervisor-agent`
- **ECS Cluster**: `prayog-prod-ecs`
- **ECS Service**: `prayog-ag-orch-prod-pinelabs-supervisor-agent`
- **Task Definition**: `prayog-prod-ecs-ag-orch-pinelabs-supervisor-agent-td`
- **Port**: `3044`
- **Health Check**: `curl -f http://localhost:3044/supervisor-pinelabs/health`
- **Jenkins Credentials**: `prayog-prod-aws`
- **Build Context**: `src/orchestrator/supervisor_agent`

**Manual Deployment (if needed):**
```bash
# Login to ECR
aws ecr get-login-password --region ap-south-1 | \
  docker login --username AWS --password-stdin \
  084375559937.dkr.ecr.ap-south-1.amazonaws.com

# Build and push image
cd src/orchestrator/supervisor_agent
docker build -t 084375559937.dkr.ecr.ap-south-1.amazonaws.com/prayog-prod-agentic-orchestrator/pinelabs-supervisor-agent:latest .
docker push 084375559937.dkr.ecr.ap-south-1.amazonaws.com/prayog-prod-agentic-orchestrator/pinelabs-supervisor-agent:latest

# Update ECS service
aws ecs update-service \
  --cluster prayog-prod-ecs \
  --service prayog-ag-orch-prod-pinelabs-supervisor-agent \
  --force-new-deployment
```

#### Transaction RCA Agent
- **ECR Repo**: `084375559937.dkr.ecr.ap-south-1.amazonaws.com/prayog-prod-agentic-orchestrator/transaction-rca-agent`
- **ECS Cluster**: `prayog-prod-ecs`
- **ECS Service**: `prayog-ag-orch-prod-transaction-rca-agent`
- **Task Definition**: `prayog-prod-ecs-ag-orch-transaction-rca-agent-td`
- **Port**: `3045`
- **Health Check**: `curl -f http://localhost:3045/rca-pinelabs/health`
- **SLIM Endpoint**: `http://3.7.70.176:46357`
- **Jenkins Credentials**: `prayog-prod-aws`
- **Build Context**: `src/orchestrator/transaction_rca_agent`

**Manual Deployment (if needed):**
```bash
# Login to ECR
aws ecr get-login-password --region ap-south-1 | \
  docker login --username AWS --password-stdin \
  084375559937.dkr.ecr.ap-south-1.amazonaws.com

# Build and push image
cd src/orchestrator/transaction_rca_agent
docker build -t 084375559937.dkr.ecr.ap-south-1.amazonaws.com/prayog-prod-agentic-orchestrator/transaction-rca-agent:latest .
docker push 084375559937.dkr.ecr.ap-south-1.amazonaws.com/prayog-prod-agentic-orchestrator/transaction-rca-agent:latest

# Get current task definition
aws ecs describe-task-definition \
  --task-definition prayog-prod-ecs-ag-orch-transaction-rca-agent-td \
  --query 'taskDefinition' > task-def.json

# Update task definition with new image and SLIM_ENDPOINT
cat task-def.json | jq --arg IMAGE "084375559937.dkr.ecr.ap-south-1.amazonaws.com/prayog-prod-agentic-orchestrator/transaction-rca-agent:latest" \
                       --arg SLIM_ENDPOINT "http://3.7.70.176:46357" '
  .containerDefinitions[0].image = $IMAGE |
  .containerDefinitions[0].environment = (
    (.containerDefinitions[0].environment // []) |
    map(select(.name != "SLIM_ENDPOINT")) +
    [{"name":"SLIM_ENDPOINT","value":$SLIM_ENDPOINT}]
  ) |
  del(.taskDefinitionArn, .revision, .status, .requiresAttributes, .compatibilities, .registeredAt, .registeredBy)
' > new-task-def.json

# Register new task definition
NEW_TASK_DEF_ARN=$(aws ecs register-task-definition \
  --cli-input-json file://new-task-def.json \
  --query 'taskDefinition.taskDefinitionArn' \
  --output text)

# Update ECS service
aws ecs update-service \
  --cluster prayog-prod-ecs \
  --service prayog-ag-orch-prod-transaction-rca-agent \
  --task-definition $NEW_TASK_DEF_ARN \
  --force-new-deployment

# Cleanup
rm -f task-def.json new-task-def.json
```

#### Frontend
- **S3 Bucket**: `pinelabs-frontend`
- **CloudFront Distribution ID**: `E29AQVB9X1DUQS`
- **Build Parameter**: `VITE_ORCHESTRATOR_API_URL` (default: `https://prod-apis.prayog.io`)
- **Jenkins Credentials**: `prayog-prod-aws`
- **Build Context**: `src/frontend`
- **Node Version**: `node18`

**Manual Deployment (if needed):**
```bash
# Set API URL (required)
export VITE_ORCHESTRATOR_API_URL=https://prod-apis.prayog.io

# Build frontend
cd src/frontend
npm install
npm run build

# Deploy to S3
aws s3 sync dist/ s3://pinelabs-frontend --delete --region ap-south-1

# Invalidate CloudFront cache
aws cloudfront create-invalidation \
  --distribution-id E29AQVB9X1DUQS \
  --paths "/*" \
  --region ap-south-1
```

## Troubleshooting

### Docker Daemon Not Running
If you see: `Cannot connect to the Docker daemon at unix:///Users/adityaraj/.docker/run/docker.sock`

**Solution:**
```bash
# Start Docker Desktop (macOS)
open -a Docker

# Or check if Docker is running
docker ps

# Wait for Docker to start, then retry
docker compose up --build
```

### Environment Variables Not Loading
If environment variables are missing:
```bash
# Make sure Pinelabs.env exists and is in the root directory
ls -la Pinelabs.env

# Source it explicitly before running docker compose
source Pinelabs.env && docker compose up --build
```

## Notes

- ✅ Production Dockerfiles do **NOT** use `--reload` (correct for production)
- ✅ Development uses `run-dev.sh` with `--reload` for hot-reloading
- ✅ All environment variables should be set in `Pinelabs.env` for local development
- ✅ Jenkins pipelines handle all AWS deployment steps automatically
- ✅ Docker Compose requires Docker Desktop to be running on macOS
- ✅ Transaction RCA Agent requires SLIM endpoint to be configured in task definition
