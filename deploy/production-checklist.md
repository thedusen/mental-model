# Production Deployment Checklist

## 🚨 CRITICAL - Security Hardening (BEFORE ANY DEPLOYMENT)

### Database Security
- [ ] **Change default Neo4j password** from `password123`
- [ ] **Generate strong JWT secret key** (minimum 32 characters)
- [ ] **Configure secure API keys** for Anthropic and Cohere
- [ ] **Set up proper CORS origins** (no wildcards in production)
- [ ] **Configure trusted hosts** for your domain
- [ ] **Enable Neo4j authentication** and disable guest access
- [ ] **Restrict Neo4j browser access** in production (port 7474)

### Application Security
- [ ] **Set ENVIRONMENT=production** to disable debug endpoints
- [ ] **Configure rate limiting** appropriate for your usage
- [ ] **Review security headers** in security.py
- [ ] **Set up proper logging levels** (avoid debug in production)
- [ ] **Configure secrets management** (never commit secrets to git)

---

## 🏗️ Infrastructure Preparation

### Cloud Provider Setup
- [ ] **Choose deployment platform** (Railway/Render/DigitalOcean/Fly.io)
- [ ] **Set up domain and SSL certificates**
- [ ] **Configure DNS records** pointing to your deployment
- [ ] **Set up monitoring and alerting**
- [ ] **Configure backup storage** (S3/equivalent)

### Resource Planning
- [ ] **Database sizing**: Start with 1GB RAM minimum for Neo4j
- [ ] **Backend sizing**: 512MB RAM minimum for FastAPI
- [ ] **Storage**: Plan for database growth and backups
- [ ] **Bandwidth**: Estimate API calls and data transfer

---

## 📦 Deployment Options (Choose One)

### Option A: Railway (Recommended for MVP)
**Cost**: ~$10/month | **Complexity**: Low | **Operational Risk**: Medium

```bash
# 1. Install Railway CLI
npm install -g @railway/cli

# 2. Login and create project
railway login
railway init mental-model

# 3. Set environment variables
railway variables set NEO4J_PASSWORD="your-secure-password"
railway variables set JWT_SECRET_KEY="your-jwt-secret-32-chars-min"
railway variables set ANTHROPIC_API_KEY="your-anthropic-key"
railway variables set COHERE_API_KEY="your-cohere-key"
railway variables set ALLOWED_ORIGINS="https://yourdomain.com"

# 4. Deploy
railway up
```

**✅ PROS**: Simple deployment, persistent volumes, automatic SSL
**❌ CONS**: Limited to US region, volume pricing scales with usage

### Option B: DigitalOcean Droplet (Best for Control)
**Cost**: ~$12/month | **Complexity**: Medium | **Operational Risk**: Low

```bash
# 1. Create Ubuntu 22.04 droplet (2GB RAM minimum)
# 2. Install Docker and Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# 3. Clone repository and configure
git clone https://github.com/yourusername/mental-model.git
cd mental-model
cp environment.template .env
# Edit .env with your values

# 4. Deploy with production compose
docker-compose -f docker-compose.prod.yml up -d

# 5. Set up SSL with Certbot
sudo apt install certbot
sudo certbot --nginx -d yourdomain.com
```

**✅ PROS**: Full control, predictable costs, SSH access
**❌ CONS**: You manage OS updates, backups, monitoring

### Option C: Render (Balanced Approach)
**Cost**: ~$15/month | **Complexity**: Low-Medium | **Operational Risk**: Medium

```bash
# 1. Connect GitHub repository to Render
# 2. Create PostgreSQL database service (if using managed DB)
# 3. Create Neo4j service using Docker
# 4. Create FastAPI service
# 5. Set environment variables in Render dashboard
```

**✅ PROS**: GitHub integration, automatic deployments, decent monitoring
**❌ CONS**: More expensive, less flexibility than VPS

---

## 🔧 Post-Deployment Configuration

### Health Monitoring Setup
- [ ] **Verify health endpoints** respond correctly:
  - `GET /api/health` - Basic health check
  - `GET /api/health/detailed` - System metrics
  - `GET /api/health/ready` - Kubernetes readiness
  - `GET /api/health/live` - Kubernetes liveness

### Backup Configuration
- [ ] **Test database backup/restore**
- [ ] **Set up automated backups** (daily recommended)
- [ ] **Configure backup retention** (30 days recommended)
- [ ] **Verify backup integrity** monthly

### Performance Optimization
- [ ] **Configure Neo4j memory settings** based on instance size
- [ ] **Set up connection pooling** for database
- [ ] **Monitor API response times**
- [ ] **Configure rate limiting** based on usage patterns

### Frontend Deployment
- [ ] **Build React application** for production
- [ ] **Deploy to static hosting** (Vercel/Netlify/Cloudflare Pages)
- [ ] **Configure environment variables** for API endpoints
- [ ] **Set up SSL and CDN**

---

## 📊 Operational Excellence

### Monitoring & Alerting
- [ ] **Set up uptime monitoring** (UptimeRobot/Pingdom)
- [ ] **Configure error tracking** (Sentry)
- [ ] **Monitor database performance**
- [ ] **Set up cost alerts** for cloud resources
- [ ] **Monitor API rate limits and usage**

### Logging Strategy
- [ ] **Centralize application logs**
- [ ] **Set up log rotation** and retention
- [ ] **Configure structured logging** (JSON format)
- [ ] **Monitor error patterns**

### Security Monitoring
- [ ] **Monitor failed authentication attempts**
- [ ] **Set up alerts for suspicious activity**
- [ ] **Regular security updates** for dependencies
- [ ] **Monitor SSL certificate expiration**

---

## 🚀 Launch Checklist

### Pre-Launch Testing
- [ ] **Load test API endpoints**
- [ ] **Test failover scenarios**
- [ ] **Verify backup/restore procedures**
- [ ] **Test all CRUD operations**
- [ ] **Validate security controls**

### Go-Live Process
- [ ] **Deploy to production**
- [ ] **Verify all services healthy**
- [ ] **Test critical user journeys**
- [ ] **Monitor error rates and performance**
- [ ] **Have rollback plan ready**

### Post-Launch Monitoring
- [ ] **Monitor system metrics** for first 24 hours
- [ ] **Check error logs** and fix issues immediately
- [ ] **Validate backup processes** within first week
- [ ] **Review performance** and optimize as needed

---

## 🔄 Ongoing Maintenance

### Weekly Tasks
- [ ] **Review error logs** and fix issues
- [ ] **Monitor performance metrics**
- [ ] **Check backup integrity**
- [ ] **Review security alerts**

### Monthly Tasks
- [ ] **Update dependencies** and security patches
- [ ] **Review resource usage** and optimize costs
- [ ] **Test disaster recovery** procedures
- [ ] **Review and rotate API keys**

### Quarterly Tasks
- [ ] **Security audit** and penetration testing
- [ ] **Capacity planning** and scaling review
- [ ] **Cost optimization** review
- [ ] **Update runbooks** and documentation

---

## 🆘 Emergency Procedures

### Incident Response
1. **Identify** the issue using monitoring tools
2. **Assess** impact and severity
3. **Communicate** status to stakeholders
4. **Mitigate** immediate impact
5. **Resolve** root cause
6. **Document** lessons learned

### Common Issues & Solutions
- **Database connectivity**: Check Neo4j service health and credentials
- **High response times**: Monitor CPU/memory usage, consider scaling
- **API rate limits**: Review usage patterns and adjust limits
- **SSL certificate expiration**: Set up automated renewal

### Rollback Procedures
- **Application rollback**: Deploy previous Docker image
- **Database rollback**: Restore from backup (data loss possible)
- **Configuration rollback**: Revert environment variables

---

## 📝 Documentation Required

- [ ] **API documentation** (Swagger/OpenAPI)
- [ ] **Runbook** for common operations
- [ ] **Architecture diagram** showing all components
- [ ] **Security procedures** and incident response
- [ ] **Backup and recovery** procedures
- [ ] **Monitoring** and alerting setup

---

## ⚠️ Operational Risk Assessment

### HIGH RISK - Address Immediately
- **No authentication** on API endpoints
- **Hardcoded credentials** in configuration
- **No backup strategy** implemented
- **No monitoring** or alerting

### MEDIUM RISK - Address Within 1 Week
- **Single point of failure** (no redundancy)
- **No rate limiting** on expensive endpoints
- **No SSL/TLS** termination
- **No error tracking**

### LOW RISK - Address Over Time
- **Manual deployment** process
- **No automated testing** in CI/CD
- **No performance optimization**
- **No capacity planning** 