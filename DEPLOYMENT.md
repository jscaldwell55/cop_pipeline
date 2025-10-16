# Deployment Guide

## Production Deployment

### 1. Environment Setup
```bash
# Create production environment file
cp .env.example .env.production

# Edit with production values
nano .env.production
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
kubectl create namespace cop-pipeline

# Create secrets
kubectl create secret generic cop-secrets \
    --from-env-file=.env.production \
    -n cop-pipeline

# Deploy
kubectl apply -f k8s/ -n cop-pipeline

# Check status
kubectl get pods -n cop-pipeline
```

### 4. Monitoring Setup
```bash
# Access Grafana
kubectl port-forward svc/grafana 3000:3000 -n cop-pipeline

# Import dashboards from config/grafana/dashboards/
```

## Scaling

### Horizontal Scaling
```yaml
# k8s/deployment.yaml
spec:
  replicas: 5  # Scale workers
```

### Database Scaling
```bash
# PostgreSQL read replicas
docker-compose -f docker-compose.prod.yml up -d --scale postgres-replica=2
```

## Security

### API Key Rotation
```bash
# Update secrets
kubectl create secret generic cop-secrets \
    --from-env-file=.env.new \
    --dry-run=client -o yaml | kubectl apply -f -

# Restart pods
kubectl rollout restart deployment/cop-pipeline -n cop-pipeline
```

### Network Security

- Enable TLS for all connections
- Use VPC/private networks
- Implement rate limiting
- Enable audit logging

## Backup & Recovery

### Database Backup
```bash
# Automated daily backups
docker exec cop-postgres pg_dump -U cop_user cop_pipeline > backup.sql
```

### Restore
```bash
docker exec -i cop-postgres psql -U cop_user cop_pipeline < backup.sql
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
   - Review PostgreSQL logs