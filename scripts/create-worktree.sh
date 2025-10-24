#!/bin/bash

# create-worktree.sh - Automated worktree creation with environment setup
# Usage: ./scripts/create-worktree.sh <worktree-name> [branch-name]

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_step() {
    echo -e "\n${BLUE}==>${NC} $1"
}

# Usage function
usage() {
    echo "Usage: $0 <worktree-name> [branch-name]"
    echo ""
    echo "Examples:"
    echo "  $0 feature-auth                          # Creates new branch 'feature/auth'"
    echo "  $0 feature-auth feature/auth-improvements # Uses existing branch"
    echo "  $0 bugfix-search main                    # Creates worktree from main branch"
    echo ""
    echo "The worktree will be created in the parent directory as:"
    echo "  ../mental-model-<worktree-name>/"
    exit 1
}

# Check arguments
if [ $# -lt 1 ] || [ $# -gt 2 ]; then
    usage
fi

WORKTREE_NAME="$1"
BRANCH_NAME="${2:-}"
WORKTREE_PATH="../mental-model-$WORKTREE_NAME"
PROJECT_ROOT="$(pwd)"

# Validate we're in the right directory
if [ ! -f "CLAUDE.md" ] || [ ! -d "backend" ] || [ ! -d "frontend" ]; then
    print_error "This script must be run from the mental-model project root directory"
    exit 1
fi

print_info "Creating worktree for Mental Model project"
print_info "Worktree name: $WORKTREE_NAME"
print_info "Worktree path: $WORKTREE_PATH"

# Check if worktree path already exists
if [ -d "$WORKTREE_PATH" ]; then
    print_error "Directory $WORKTREE_PATH already exists"
    exit 1
fi

# Step 1: Create the worktree
print_step "Creating Git worktree"

if [ -n "$BRANCH_NAME" ]; then
    # Use provided branch name
    if git show-ref --verify --quiet refs/heads/"$BRANCH_NAME"; then
        # Branch exists locally
        print_info "Using existing local branch: $BRANCH_NAME"
        git worktree add "$WORKTREE_PATH" "$BRANCH_NAME"
    elif git show-ref --verify --quiet refs/remotes/origin/"$BRANCH_NAME"; then
        # Branch exists on remote
        print_info "Using existing remote branch: $BRANCH_NAME"
        git worktree add "$WORKTREE_PATH" --track origin/"$BRANCH_NAME"
    else
        # Create new branch
        print_info "Creating new branch: $BRANCH_NAME"
        git worktree add "$WORKTREE_PATH" -b "$BRANCH_NAME"
    fi
else
    # Auto-generate branch name
    AUTO_BRANCH="feature/$(echo "$WORKTREE_NAME" | tr '-' '/')"
    print_info "Auto-generating branch: $AUTO_BRANCH"
    git worktree add "$WORKTREE_PATH" -b "$AUTO_BRANCH"
fi

print_success "Worktree created successfully"

# Step 2: Navigate to worktree
cd "$WORKTREE_PATH"
print_info "Working in: $(pwd)"

# Step 3: Copy environment file
print_step "Setting up environment configuration"

if [ -f "$PROJECT_ROOT/.env" ]; then
    cp "$PROJECT_ROOT/.env" .env
    print_success "Environment file copied"
else
    print_warning "No .env file found in main project. You may need to create one."
    if [ -f "$PROJECT_ROOT/environment.template" ]; then
        cp "$PROJECT_ROOT/environment.template" .env
        print_info "Copied environment template - please configure .env"
    fi
fi

# Step 4: Set up Python backend
print_step "Setting up Python backend environment"

cd backend

# Create virtual environment
print_info "Creating Python virtual environment..."
python3 -m venv venv

# Activate virtual environment
print_info "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
print_info "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

print_success "Python backend environment ready"

# Step 5: Set up React frontend
cd ../frontend
print_step "Setting up React frontend environment"

# Install dependencies
print_info "Installing Node.js dependencies..."
npm install

print_success "React frontend environment ready"

# Step 6: Set up Git hooks
cd ..
print_step "Setting up Git hooks"

if [ -f "setup-hooks.sh" ]; then
    ./setup-hooks.sh
    print_success "Git hooks installed"
else
    print_warning "setup-hooks.sh not found - skipping Git hooks setup"
fi

# Step 7: Verify setup
print_step "Verifying setup"

# Check Python environment
cd backend
source venv/bin/activate
PYTHON_PATH=$(which python)
PIP_PACKAGES=$(pip list | wc -l)
print_info "Python executable: $PYTHON_PATH"
print_info "Installed packages: $PIP_PACKAGES"

# Check Node environment
cd ../frontend
NODE_MODULES_SIZE=$(du -sh node_modules 2>/dev/null | cut -f1 || echo "N/A")
print_info "Node modules size: $NODE_MODULES_SIZE"

# Final information
cd ..
CURRENT_BRANCH=$(git branch --show-current)
WORKTREE_ABS_PATH=$(pwd)

print_step "Setup Complete!"
print_success "Worktree created and configured successfully"
echo ""
print_info "Worktree Details:"
echo "  Location: $WORKTREE_ABS_PATH"
echo "  Branch: $CURRENT_BRANCH"
echo "  Python venv: backend/venv/"
echo "  Node modules: frontend/node_modules/"
echo ""
print_info "Next Steps:"
echo "  1. cd $WORKTREE_PATH"
echo "  2. Start Claude Code: claude"
echo "  3. Or start development servers:"
echo "     Backend:  cd backend && source venv/bin/activate && python main.py"
echo "     Frontend: cd frontend && npm start"
echo "     Database: docker compose up (from any worktree)"
echo ""
print_info "To remove this worktree later:"
echo "  git worktree remove $WORKTREE_PATH"
echo ""

# Optional: Ask if user wants to start Claude Code
read -p "Start Claude Code in the new worktree? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_info "Starting Claude Code..."
    claude
fi