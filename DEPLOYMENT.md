# Deployment Guide

## Production Deployment

### 1. Environment Setup
```bash
# Create production environment file
cp .env .env.production

# Edit with production values
nano .env.production

# Update with production credentials and settings
# - Use strong passwords for POSTGRES_PASSWORD and REDIS_PASSWORD
# - Set appropriate MAX_CONCURRENT_REQUESTS based on your API limits
# - Configure WANDB_API_KEY if using Weights & Biases
```

### 2. Docker Deployment
```bash
# Build production image
docker-compose -f docker-compose.prod.yml build

# Start services
docker-compose -f docker-compose.prod.yml up -d

# Check logs
docker-compose logs -f cop-pipeline
```

### 3. Kubernetes Deployment
```bash
# Create namespace
kubectl apply -f k8s/namespace.yaml

# Create secrets
kubectl create secret generic cop-secrets \
    --from-env-file=.env.production \
    -n cop-pipeline

# Apply configurations
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml

# Check status
kubectl get pods -n cop-pipeline
kubectl get svc -n cop-pipeline
```

### 4. Monitoring Setup
```bash
# Access Grafana (if deployed in k8s)
kubectl port-forward svc/grafana 3000:3000 -n cop-pipeline

# For Docker deployments, Grafana is accessible at:
# http://localhost:3000 (default credentials: admin/admin)

# Import dashboards from config/grafana/dashboards/ if needed
```

## Scaling

### Horizontal Scaling (Kubernetes)
```bash
# Scale deployment
kubectl scale deployment cop-pipeline --replicas=5 -n cop-pipeline

# Or edit deployment.yaml
# spec:
#   replicas: 5
```

### Vertical Scaling (Docker)
```bash
# Update resource limits in docker-compose.prod.yml
# services:
#   cop-pipeline:
#     deploy:
#       resources:
#         limits:
#           cpus: '2'
#           memory: 4G
```

## Security

### API Key Rotation

**For Kubernetes:**
```bash
# Update secrets
kubectl create secret generic cop-secrets \
    --from-env-file=.env.new \
    --dry-run=client -o yaml | kubectl apply -f -

# Restart pods
kubectl rollout restart deployment/cop-pipeline -n cop-pipeline
```

**For Docker:**
```bash
# Update .env file with new keys
nano .env

# Restart services
docker-compose restart cop-pipeline
```

### Network Security

- Enable TLS for all connections
- Use VPC/private networks
- Implement rate limiting
- Enable audit logging

## Backup & Recovery

### Database Backup
```bash
# Create backup directory
mkdir -p backups

# Manual backup
docker exec cop-postgres pg_dump -U cop_user cop_pipeline > backups/backup_$(date +%Y%m%d_%H%M%S).sql

# Automated daily backups (add to cron)
# 0 2 * * * cd /path/to/cop_pipeline && docker exec cop-postgres pg_dump -U cop_user cop_pipeline > backups/backup_$(date +\%Y\%m\%d).sql
```

### Restore
```bash
# Restore from backup
docker exec -i cop-postgres psql -U cop_user cop_pipeline < backups/backup_20241016.sql
```

## Troubleshooting

### Common Issues

1. **High memory usage**
   - Reduce `max_concurrent_requests`
   - Enable Redis caching
   - Scale horizontally

2. **Slow responses**
   - Check API rate limits
   - Increase timeout values
   - Monitor LLM provider status

3. **Database connection errors**
   - Check connection pool settings
   - Verify network connectivity
   - Review PostgreSQL logs: `docker-compose logs postgres`
   - Verify credentials in .env match database settings

## Health Checks

### Docker Deployment
```bash
# Check all services
docker-compose ps

# Check logs
docker-compose logs -f cop-pipeline

# Test database connection
python cli.py check-setup
```

### Kubernetes Deployment
```bash
# Check pod status
kubectl get pods -n cop-pipeline

# Check logs
kubectl logs -f deployment/cop-pipeline -n cop-pipeline

# Check services
kubectl get svc -n cop-pipeline
```

## Environment Variables Reference

See `.env` file for all configuration options. Key production settings:

- `MAX_CONCURRENT_REQUESTS`: Limit parallel attacks (default: 10)
- `MAX_ITERATIONS`: Maximum refinement loops (default: 10)
- `JAILBREAK_THRESHOLD`: Success threshold score (default: 10)
- `DEFAULT_RED_TEAMING_AGENT`: Model for attack generation (default: grok-2)
- `DEFAULT_JUDGE_LLM`: Model for evaluation (default: gpt-4o)
- `WANDB_MODE`: Set to "disabled" to skip Weights & Biases