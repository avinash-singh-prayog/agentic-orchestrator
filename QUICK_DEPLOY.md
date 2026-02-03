# Quick Deployment Reference

## 🚀 Deploy Everything (All Services)

```bash
./manual-deploy.sh all
```

## 📦 Deploy Individual Services

```bash
# Supervisor Agent only
./manual-deploy.sh supervisor

# RCA Agent only  
./manual-deploy.sh rca

# Frontend only
./manual-deploy.sh frontend
```

## ✅ Before You Start

1. **AWS CLI configured?**
   ```bash
   aws sts get-caller-identity
   ```

2. **Docker running?**
   ```bash
   docker ps
   ```

3. **jq installed?**
   ```bash
   jq --version
   # If not: brew install jq (macOS) or apt-get install jq (Linux)
   ```

4. **Node.js installed?** (for frontend)
   ```bash
   node --version
   ```

## 📋 What Gets Deployed

### Supervisor Agent
- Builds Docker image
- Pushes to ECR: `prayog-prod-agentic-orchestrator/pinelabs-supervisor-agent`
- Updates ECS service: `prayog-ag-orch-prod-pinelabs-supervisor-agent`
- Port: `3044`

### RCA Agent
- Builds Docker image
- Pushes to ECR: `prayog-prod-agentic-orchestrator/transaction-rca-agent`
- Updates ECS service: `prayog-ag-orch-prod-transaction-rca-agent`
- Port: `3045`
- SLIM Endpoint: `http://3.7.70.176:46357`

### Frontend
- Builds React app
- Deploys to S3: `pinelabs-frontend`
- Invalidates CloudFront: `E29AQVB9X1DUQS`
- API URL: `https://prod-apis.prayog.io`

## ⏱️ Expected Time

- Supervisor: ~3-5 minutes
- RCA: ~3-5 minutes  
- Frontend: ~2-3 minutes
- All: ~8-12 minutes

## 🔍 Monitor Deployment

```bash
# Check ECS service status
aws ecs describe-services \
  --cluster prayog-prod-ecs \
  --services prayog-ag-orch-prod-pinelabs-supervisor-agent \
  --region ap-south-1
```

Or check AWS Console:
- ECS: https://console.aws.amazon.com/ecs/v2/clusters/prayog-prod-ecs/services
- ECR: https://console.aws.amazon.com/ecr/repositories

## 🆘 If Something Fails

See `MANUAL_DEPLOYMENT_GUIDE.md` for detailed troubleshooting and manual steps.

## 💡 Tips

- The script automatically handles ECR login, building, pushing, and ECS updates
- Build numbers are timestamp-based (e.g., `20260130191215`)
- All images are tagged with both `:BUILD_NUMBER` and `:latest`
- ECS deployments use `--force-new-deployment` to ensure new tasks start
