#!/bin/bash

# Mental Model - Quick Cloud Deployment Script
# This script automates the deployment process for various cloud providers

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}"
    exit 1
}

success() {
    echo -e "${GREEN}[SUCCESS] $1${NC}"
}

# Check if environment file exists
check_environment() {
    if [ ! -f ".env" ]; then
        error "Environment file (.env) not found. Please copy environment.template to .env and configure it."
    fi
    
    # Check for critical variables
    if ! grep -q "NEO4J_PASSWORD=your-secure-password" .env; then
        warn "Please update NEO4J_PASSWORD in .env file"
    fi
    
    if ! grep -q "JWT_SECRET_KEY=your-super-secret" .env; then
        warn "Please update JWT_SECRET_KEY in .env file"
    fi
    
    if ! grep -q "ANTHROPIC_API_KEY=your-anthropic" .env; then
        warn "Please update ANTHROPIC_API_KEY in .env file"
    fi
    
    success "Environment file validation completed"
}

# Railway deployment
deploy_railway() {
    log "Deploying to Railway..."
    
    # Check if Railway CLI is installed
    if ! command -v railway &> /dev/null; then
        error "Railway CLI not found. Install with: npm install -g @railway/cli"
    fi
    
    # Check if logged in
    if ! railway whoami &> /dev/null; then
        log "Please login to Railway first:"
        railway login
    fi
    
    # Create project if it doesn't exist
    if ! railway status &> /dev/null; then
        log "Creating new Railway project..."
        railway init mental-model
    fi
    
    # Set environment variables from .env file
    log "Setting environment variables..."
    while IFS= read -r line; do
        if [[ $line =~ ^[^#]*= ]]; then
            key=$(echo "$line" | cut -d= -f1)
            value=$(echo "$line" | cut -d= -f2-)
            railway variables set "$key=$value"
        fi
    done < .env
    
    # Deploy
    log "Starting deployment..."
    railway up
    
    success "Railway deployment completed!"
    log "Check your deployment at: $(railway status --json | jq -r '.deployments[0].url')"
}

# DigitalOcean Droplet deployment
deploy_digitalocean() {
    log "Setting up DigitalOcean deployment instructions..."
    
    cat << EOF
To deploy on DigitalOcean Droplet:

1. Create a new Droplet (Ubuntu 22.04, 2GB RAM minimum)
2. SSH into your droplet
3. Run these commands:

# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
sudo usermod -aG docker \$USER

# Install Docker Compose
sudo apt install docker-compose-plugin

# Clone repository
git clone https://github.com/yourusername/mental-model.git
cd mental-model

# Configure environment
cp environment.template .env
nano .env  # Edit with your values

# Deploy
docker compose -f docker-compose.prod.yml up -d

# Set up SSL (replace yourdomain.com with your domain)
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com

4. Your application will be available at https://yourdomain.com
EOF
    
    success "DigitalOcean deployment instructions provided"
}

# Render deployment
deploy_render() {
    log "Setting up Render deployment..."
    
    # Create render.yaml if it doesn't exist
    if [ ! -f "render.yaml" ]; then
        log "Creating render.yaml configuration..."
        cat > render.yaml << EOF
services:
  - type: web
    name: mental-model-backend
    env: docker
    dockerfilePath: ./Dockerfile
    envVars:
      - key: ENVIRONMENT
        value: production
      - key: NEO4J_URI
        fromService:
          type: pserv
          name: mental-model-neo4j
          property: connectionString
      - key: NEO4J_PASSWORD
        fromService:
          type: pserv
          name: mental-model-neo4j
          property: password
      - key: ANTHROPIC_API_KEY
        sync: false
      - key: COHERE_API_KEY
        sync: false
      - key: JWT_SECRET_KEY
        generateValue: true
      - key: ALLOWED_ORIGINS
        value: https://mental-model-frontend.onrender.com
    
  - type: pserv
    name: mental-model-neo4j
    env: docker
    dockerImage: neo4j:5.25.1
    envVars:
      - key: NEO4J_PLUGINS
        value: '["apoc"]'
      - key: NEO4J_dbms_security_procedures_unrestricted
        value: apoc.*
    disk:
      name: neo4j-data
      mountPath: /data
      sizeGB: 10

  - type: web
    name: mental-model-frontend
    env: static
    buildCommand: cd frontend && npm install && npm run build
    staticPublishPath: ./frontend/build
    envVars:
      - key: REACT_APP_API_URL
        fromService:
          type: web
          name: mental-model-backend
          property: host
EOF
        success "render.yaml created"
    fi
    
    cat << EOF
To deploy on Render:

1. Push your code to GitHub (including the generated render.yaml)
2. Go to https://render.com and connect your GitHub repository
3. Render will automatically detect the render.yaml and create services
4. Set the following environment variables in Render dashboard:
   - ANTHROPIC_API_KEY
   - COHERE_API_KEY
5. Deploy!

Your application will be available at the provided Render URL.
EOF
    
    success "Render deployment setup completed"
}

# Fly.io deployment
deploy_flyio() {
    log "Setting up Fly.io deployment..."
    
    # Check if flyctl is installed
    if ! command -v flyctl &> /dev/null; then
        error "Fly.io CLI not found. Install from: https://fly.io/docs/hands-on/install-flyctl/"
    fi
    
    # Check if logged in
    if ! flyctl auth whoami &> /dev/null; then
        log "Please login to Fly.io first:"
        flyctl auth login
    fi
    
    # Create fly.toml if it doesn't exist
    if [ ! -f "fly.toml" ]; then
        log "Creating fly.toml configuration..."
        flyctl launch --no-deploy
    fi
    
    # Set secrets from .env file
    log "Setting secrets..."
    while IFS= read -r line; do
        if [[ $line =~ ^[^#]*= ]]; then
            key=$(echo "$line" | cut -d= -f1)
            value=$(echo "$line" | cut -d= -f2-)
            if [[ $key == *"PASSWORD"* || $key == *"KEY"* || $key == *"SECRET"* ]]; then
                flyctl secrets set "$key=$value"
            fi
        fi
    done < .env
    
    # Deploy
    log "Starting deployment..."
    flyctl deploy
    
    success "Fly.io deployment completed!"
    log "Check your deployment at: $(flyctl status --json | jq -r '.Hostname')"
}

# Main deployment function
main() {
    log "Mental Model - Cloud Deployment Script"
    echo "========================================"
    
    # Check prerequisites
    check_environment
    
    echo ""
    echo "Choose your deployment platform:"
    echo "1) Railway (Recommended for MVP - ~$10/month)"
    echo "2) DigitalOcean Droplet (Best control - ~$12/month)"
    echo "3) Render (Balanced approach - ~$15/month)"
    echo "4) Fly.io (Global edge deployment - ~$8/month)"
    echo "5) Exit"
    
    read -p "Enter your choice (1-5): " choice
    
    case $choice in
        1)
            deploy_railway
            ;;
        2)
            deploy_digitalocean
            ;;
        3)
            deploy_render
            ;;
        4)
            deploy_flyio
            ;;
        5)
            log "Exiting..."
            exit 0
            ;;
        *)
            error "Invalid choice. Please select 1-5."
            ;;
    esac
    
    echo ""
    log "Deployment completed! Don't forget to:"
    echo "- Set up monitoring and alerting"
    echo "- Configure backups"
    echo "- Test all functionality"
    echo "- Review the production checklist at deploy/production-checklist.md"
}

# Run main function
main "$@" 