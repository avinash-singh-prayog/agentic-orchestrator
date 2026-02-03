# Manual Deployment Guide

This guide helps you deploy services manually when Jenkins is down.

## Prerequisites

Before running the deployment script, ensure you have:

1. **AWS CLI installed and configured**
   ```bash
   aws --version
   aws configure  # If not configured
   ```

2. **Docker installed and running**
   ```bash
   docker --version
   docker ps  # Should work without errors
   ```

3. **jq installed** (for JSON processing)
   ```bash
   # macOS
   brew install jq
   
   # Linux
   sudo apt-get install jq  # or yum install jq
   ```

4. **Node.js 18+ installed** (for frontend deployment)
   ```bash
   node --version
   ```

5. **AWS credentials with appropriate permissions**
   - ECR push permissions
   - ECS update permissions
   - S3 write permissions (for frontend)
   - CloudFront invalidation permissions

## Quick Start

### Deploy All Services
```bash
./manual-deploy.sh all
```

### Deploy Individual Services
```bash
# Deploy only Supervisor Agent
./manual-deploy.sh supervisor

# Deploy only RCA Agent
./manual-deploy.sh rca

# Deploy only Frontend
./manual-deploy.sh frontend
```

## What the Script Does

### For Supervisor & RCA Agents:
1. ✅ Logs into AWS ECR
2. ✅ Builds Docker image with build number tag
3. ✅ Pushes image to ECR (both `:latest` and `:BUILD_NUMBER`)
4. ✅ Fetches current ECS task definition
5. ✅ Updates task definition with new image
6. ✅ Registers new task definition revision
7. ✅ Updates ECS service to use new task definition
8. ✅ Forces new deployment

### For Frontend:
1. ✅ Builds frontend with production API URL
2. ✅ Syncs build files to S3 bucket
3. ✅ Invalidates CloudFront cache

## Service Details

### Supervisor Agent
- **ECR Repo**: `084375559937.dkr.ecr.ap-south-1.amazonaws.com/prayog-prod-agentic-orchestrator/pinelabs-supervisor-agent`
- **ECS Service**: `prayog-ag-orch-prod-pinelabs-supervisor-agent`
- **Task Definition**: `prayog-prod-ecs-ag-orch-pinelabs-supervisor-agent-td`
- **Port**: `3044`
- **Health Check**: `http://localhost:3044/supervisor-pinelabs/health`

### Transaction RCA Agent
- **ECR Repo**: `084375559937.dkr.ecr.ap-south-1.amazonaws.com/prayog-prod-agentic-orchestrator/transaction-rca-agent`
- **ECS Service**: `prayog-ag-orch-prod-transaction-rca-agent`
- **Task Definition**: `prayog-prod-ecs-ag-orch-transaction-rca-agent-td`
- **Port**: `3045`
- **SLIM Endpoint**: `http://3.7.70.176:46357`
- **Health Check**: `http://localhost:3045/rca-pinelabs/health`

### Frontend
- **S3 Bucket**: `pinelabs-frontend`
- **CloudFront Distribution**: `E29AQVB9X1DUQS`
- **API URL**: `https://prod-apis.prayog.io` (default)

## Customizing Frontend API URL

If you need to use a different API URL for the frontend:

```bash
export VITE_ORCHESTRATOR_API_URL=https://your-api-url.com
./manual-deploy.sh frontend
```

## Monitoring Deployments

After running the script, monitor your deployments:

### Check ECS Service Status
```bash
# Supervisor Agent
aws ecs describe-services \
  --cluster prayog-prod-ecs \
  --services prayog-ag-orch-prod-pinelabs-supervisor-agent \
  --region ap-south-1

# RCA Agent
aws ecs describe-services \
  --cluster prayog-prod-ecs \
  --services prayog-ag-orch-prod-transaction-rca-agent \
  --region ap-south-1
```

### Check Running Tasks
```bash
aws ecs list-tasks \
  --cluster prayog-prod-ecs \
  --service-name prayog-ag-orch-prod-pinelabs-supervisor-agent \
  --region ap-south-1
```

### View Task Logs
```bash
# Get log group name from task definition, then:
aws logs tail /ecs/prayog-prod-ecs-ag-orch-pinelabs-supervisor-agent-td --follow
```

### AWS Console
- **ECS**: https://console.aws.amazon.com/ecs/v2/clusters/prayog-prod-ecs/services
- **ECR**: https://console.aws.amazon.com/ecr/repositories
- **CloudWatch Logs**: https://console.aws.amazon.com/cloudwatch/home?region=ap-south-1#logsV2:log-groups

## Troubleshooting

### Docker Build Fails
- Ensure Docker is running: `docker ps`
- Check disk space: `df -h`
- Try cleaning up: `docker system prune -a`

### Platform Mismatch Error (CannotPullContainerError)
If you see errors like `image Manifest does not contain descriptor matching platform 'linux/amd64'`:
- **Root Cause**: Images were built for the wrong platform (e.g., `linux/arm64` on Apple Silicon Macs)
- **Solution**: Always use `--platform linux/amd64` when building Docker images for ECS
- The deployment script now includes this flag automatically
- If building manually, ensure you use: `docker build --platform linux/amd64 ...`

### ECR Login Fails
- Verify AWS credentials: `aws sts get-caller-identity`
- Check region: `aws configure get region`
- Ensure ECR repository exists

### Task Definition Update Fails
- Verify task definition name is correct
- Check IAM permissions for ECS
- Ensure task definition JSON is valid

### Frontend Build Fails
- Check Node.js version: `node --version` (should be 18+)
- Clear node_modules and reinstall: `rm -rf node_modules && npm install`
- Check for build errors in output

### S3 Sync Fails
- Verify S3 bucket exists and is accessible
- Check IAM permissions for S3
- Ensure bucket name is correct

## Manual Steps (If Script Fails)

If the script fails at any step, you can run individual commands:

### Supervisor Agent - Manual Steps

```bash
# 1. Login to ECR
aws ecr get-login-password --region ap-south-1 | \
  docker login --username AWS --password-stdin \
  084375559937.dkr.ecr.ap-south-1.amazonaws.com

# 2. Build and push (IMPORTANT: Use --platform linux/amd64 for ECS compatibility)
cd src/orchestrator/supervisor_agent
docker build --platform linux/amd64 -t 084375559937.dkr.ecr.ap-south-1.amazonaws.com/prayog-prod-agentic-orchestrator/pinelabs-supervisor-agent:latest .
docker push 084375559937.dkr.ecr.ap-south-1.amazonaws.com/prayog-prod-agentic-orchestrator/pinelabs-supervisor-agent:latest

# 3. Update ECS service (simplest method - uses latest tag)
aws ecs update-service \
  --cluster prayog-prod-ecs \
  --service prayog-ag-orch-prod-pinelabs-supervisor-agent \
  --force-new-deployment \
  --region ap-south-1
```

### RCA Agent - Manual Steps

```bash
# 1. Login to ECR
aws ecr get-login-password --region ap-south-1 | \
  docker login --username AWS --password-stdin \
  084375559937.dkr.ecr.ap-south-1.amazonaws.com

# 2. Build and push (IMPORTANT: Use --platform linux/amd64 for ECS compatibility)
cd src/orchestrator/transaction_rca_agent
docker build --platform linux/amd64 -t 084375559937.dkr.ecr.ap-south-1.amazonaws.com/prayog-prod-agentic-orchestrator/transaction-rca-agent:latest .
docker push 084375559937.dkr.ecr.ap-south-1.amazonaws.com/prayog-prod-agentic-orchestrator/transaction-rca-agent:latest

# 3. Get and update task definition
aws ecs describe-task-definition \
  --task-definition prayog-prod-ecs-ag-orch-transaction-rca-agent-td \
  --query 'taskDefinition' > task-def.json

# Edit task-def.json to update image and SLIM_ENDPOINT, then:
aws ecs register-task-definition --cli-input-json file://task-def.json

# 4. Update service
aws ecs update-service \
  --cluster prayog-prod-ecs \
  --service prayog-ag-orch-prod-transaction-rca-agent \
  --force-new-deployment \
  --region ap-south-1
```

### Frontend - Manual Steps

```bash
# 1. Build
cd src/frontend
export VITE_ORCHESTRATOR_API_URL=https://prod-apis.prayog.io
npm install
npm run build

# 2. Deploy to S3
aws s3 sync dist/ s3://pinelabs-frontend --delete --region ap-south-1

# 3. Invalidate CloudFront
aws cloudfront create-invalidation \
  --distribution-id E29AQVB9X1DUQS \
  --paths "/*" \
  --region ap-south-1
```

## Notes

- The script uses timestamp-based build numbers (format: `YYYYMMDDHHMMSS`)
- Docker images are tagged with both `:BUILD_NUMBER` and `:latest`
- ECS deployments typically take 2-5 minutes to complete
- The script cleans up temporary files and local Docker images after deployment
- All deployments use `--force-new-deployment` to ensure new tasks are started

## Support

If you encounter issues:
1. Check AWS Console for error messages
2. Review CloudWatch logs for application errors
3. Verify all prerequisites are installed
4. Ensure AWS credentials have necessary permissions
