# PineLabs Deployment Guide

This guide covers the deployment of PineLabs-specific services to AWS Account `084375559937`.

## Services Overview

1. **Supervisor Agent** - Port `3044`, API Prefix: `/supervisor-pinelabs`
2. **Transaction RCA Agent** - Port `3045`, API Prefix: `/rca-pinelabs`
3. **Frontend** - S3 + CloudFront deployment

## Pre-Deployment Checklist

### AWS Account Setup (084375559937)

1. **ECR Repositories** - Create the following repositories:
   ```bash
   aws ecr create-repository --repository-name agentic-orchestrator/supervisor-agent-pinelabs --region ap-south-1
   aws ecr create-repository --repository-name agentic-orchestrator/transaction-rca-agent-pinelabs --region ap-south-1
   ```

2. **ECS Cluster** - Ensure cluster exists:
   - Cluster Name: `prayog-ecs` (or update in Jenkinsfiles)
   - Region: `ap-south-1`

3. **ECS Services** - Create initial services (first time only):
   - Service: `supervisor-agent-pinelabs-service`
   - Service: `transaction-rca-agent-pinelabs-service`
   - Task definitions will be created automatically on first deployment

4. **S3 Bucket** - For frontend:
   ```bash
   aws s3 mb s3://agentic-orchestrator-frontend-pinelabs-assets --region ap-south-1
   ```

5. **CloudFront Distribution** - Create distribution pointing to S3 bucket
   - Update `CLOUDFRONT_ID` in `src/frontend/Jenkinsfile.pinelabs` after creation

6. **Security Groups** - Ensure ECS tasks can reach SLIM Transporter:
   - Outbound rule: Allow TCP port `46357` to `3.7.70.176`
   - Or configure VPC peering if using private connectivity

### Jenkins Setup

1. **AWS Credentials** - Ensure Jenkins has credentials for account `084375559937`:
   - Credential ID: `aws-creds` (update if different)
   - Must have permissions for: ECR, ECS, S3, CloudFront

2. **Required Jenkins Plugins**:
   - Pipeline
   - AWS CLI (or configure AWS CLI in Jenkins agent)

## Deployment Steps

### 1. Supervisor Agent Deployment

**Jenkinsfile**: `src/orchestrator/supervisor_agent/Jenkinsfile.pinelabs`

**Steps**:
1. Go to Jenkins dashboard
2. Click "New Item" → Select "Pipeline"
3. Name: `supervisor-agent-pinelabs-deploy`
4. Configure:
   - **Pipeline Definition**: Pipeline script from SCM
   - **SCM**: Git
   - **Repository URL**: Your repository URL
   - **Branch**: PineLabs branch
   - **Script Path**: `src/orchestrator/supervisor_agent/Jenkinsfile.pinelabs`
5. Click "Save"
6. Click "Build Now"

**What it does**:
- Builds Docker image
- Pushes to ECR: `084375559937.dkr.ecr.ap-south-1.amazonaws.com/agentic-orchestrator/supervisor-agent-pinelabs`
- Updates ECS task definition with:
  - Port: `3044`
  - Health check: `GET /supervisor-pinelabs/health`
  - Environment: `SLIM_ENDPOINT=http://3.7.70.176:46357`
- Deploys to ECS service: `supervisor-agent-pinelabs-service`

**Health Check Endpoint**: `http://<service-url>:3044/supervisor-pinelabs/health`

### 2. Transaction RCA Agent Deployment

**Jenkinsfile**: `src/orchestrator/transaction_rca_agent/Jenkinsfile.pinelabs`

**Steps**:
1. Go to Jenkins dashboard
2. Click "New Item" → Select "Pipeline"
3. Name: `transaction-rca-agent-pinelabs-deploy`
4. Configure:
   - **Pipeline Definition**: Pipeline script from SCM
   - **SCM**: Git
   - **Repository URL**: Your repository URL
   - **Branch**: PineLabs branch
   - **Script Path**: `src/orchestrator/transaction_rca_agent/Jenkinsfile.pinelabs`
5. Click "Save"
6. Click "Build Now"

**What it does**:
- Builds Docker image
- Pushes to ECR: `084375559937.dkr.ecr.ap-south-1.amazonaws.com/agentic-orchestrator/transaction-rca-agent-pinelabs`
- Updates ECS task definition with:
  - Port: `3045`
  - Health check: `GET /rca-pinelabs/health`
  - Environment: `SLIM_ENDPOINT=http://3.7.70.176:46357`
- Deploys to ECS service: `transaction-rca-agent-pinelabs-service`

**Health Check Endpoint**: `http://<service-url>:3045/rca-pinelabs/health`

### 3. Frontend Deployment

**Jenkinsfile**: `src/frontend/Jenkinsfile.pinelabs`

**Steps**:
1. Go to Jenkins dashboard
2. Click "New Item" → Select "Pipeline"
3. Name: `frontend-pinelabs-deploy`
4. Configure:
   - **Pipeline Definition**: Pipeline script from SCM
   - **SCM**: Git
   - **Repository URL**: Your repository URL
   - **Branch**: PineLabs branch
   - **Script Path**: `src/frontend/Jenkinsfile.pinelabs`
5. **Update CloudFront ID** in Jenkinsfile if different
6. Click "Save"
7. Click "Build Now"

**What it does**:
- Builds React frontend
- Syncs `dist/` folder to S3: `agentic-orchestrator-frontend-pinelabs-assets`
- Invalidates CloudFront cache

**Note**: Frontend uses API endpoints with PineLabs prefixes:
- `/supervisor-pinelabs/*` for supervisor agent
- `/rca-pinelabs/*` for transaction RCA agent

## Verification Steps

### 1. Check ECS Services

```bash
# Check supervisor agent
aws ecs describe-services \
  --cluster prayog-ecs \
  --services supervisor-agent-pinelabs-service \
  --region ap-south-1 \
  --profile pinelabs-account

# Check transaction RCA agent
aws ecs describe-services \
  --cluster prayog-ecs \
  --services transaction-rca-agent-pinelabs-service \
  --region ap-south-1 \
  --profile pinelabs-account
```

### 2. Test Health Checks

```bash
# Supervisor Agent Health
curl http://<supervisor-service-url>:3044/supervisor-pinelabs/health

# Transaction RCA Agent Health
curl http://<rca-service-url>:3045/rca-pinelabs/health
```

Expected response:
```json
{"status": "ok"}
```

### 3. Test API Endpoints

```bash
# Supervisor Agent - Run Agent
curl -X POST http://<supervisor-service-url>:3044/supervisor-pinelabs/v1/agent/run \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Test message", "tenant_id": "test", "user_id": "test"}'

# Transaction RCA Agent - Health
curl http://<rca-service-url>:3045/rca-pinelabs/health
```

### 4. Check SLIM Connectivity

Verify that services can connect to SLIM Transporter:
- Check ECS task logs for SLIM connection messages
- Ensure security groups allow outbound to `3.7.70.176:46357`

## Configuration Summary

| Service | Port | API Prefix | Health Check | ECR Repository |
|---------|------|------------|--------------|----------------|
| Supervisor Agent | 3044 | `/supervisor-pinelabs` | `/supervisor-pinelabs/health` | `agentic-orchestrator/supervisor-agent-pinelabs` |
| Transaction RCA Agent | 3045 | `/rca-pinelabs` | `/rca-pinelabs/health` | `agentic-orchestrator/transaction-rca-agent-pinelabs` |
| Frontend | - | - | - | S3: `agentic-orchestrator-frontend-pinelabs-assets` |

## Environment Variables

### Supervisor Agent
- `SLIM_ENDPOINT`: `http://3.7.70.176:46357` (automatically set by Jenkins)
- `DATABASE_URL`: PostgreSQL connection string
- `SUPERVISOR_LLM`: LLM model identifier
- `OPENROUTER_API_KEY`: API key for LLM provider
- Additional variables as needed

### Transaction RCA Agent
- `SLIM_ENDPOINT`: `http://3.7.70.176:46357` (automatically set by Jenkins)
- `TRANSACTION_RCA_AGENT_LLM`: LLM model identifier
- `OPENROUTER_API_KEY`: API key for LLM provider
- Additional variables as needed

## Troubleshooting

### Service Not Starting
1. Check ECS task logs in CloudWatch
2. Verify health check is passing
3. Check security group rules
4. Verify environment variables are set correctly

### SLIM Connection Issues
1. Verify `SLIM_ENDPOINT` environment variable is set
2. Check security group allows outbound to `3.7.70.176:46357`
3. Test connectivity from ECS task:
   ```bash
   curl http://3.7.70.176:46357/health
   ```

### Health Check Failing
1. Verify service is running on correct port
2. Check API prefix matches (`/supervisor-pinelabs` or `/rca-pinelabs`)
3. Review application logs for errors

### Frontend Not Loading
1. Verify S3 bucket sync completed
2. Check CloudFront distribution is active
3. Verify CloudFront invalidation completed
4. Check browser console for API errors

## Rollback Procedure

If deployment fails:

1. **ECS Services**: Use previous task definition revision
   ```bash
   aws ecs update-service \
     --cluster prayog-ecs \
     --service <service-name> \
     --task-definition <previous-revision-arn> \
     --force-new-deployment
   ```

2. **Frontend**: Revert S3 bucket to previous version (if versioning enabled)

## Next Steps

After successful deployment:
1. Configure load balancer/ALB if needed
2. Set up monitoring and alerts
3. Configure auto-scaling policies
4. Set up CI/CD triggers (webhooks, branch-based, etc.)
