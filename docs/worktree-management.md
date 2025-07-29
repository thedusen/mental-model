# Git Worktree Management Guide for Mental Model Project

This guide provides comprehensive instructions for using Git worktrees with the Mental Model project and Claude Code to enable parallel development workflows.

## 🤖 Claude Code Intelligent Worktree Management

### Quick Worktree Refresh Workflow

For refreshing existing worktrees to match the development branch, you can use this simple slash command:

**Use the custom slash command:**
```bash
/refresh-worktrees A B
```

This command will automatically:
1. Remove existing worktrees for the specified branches
2. Delete and recreate the branches from development
3. Create fresh worktrees based on current development branch
4. Verify the setup

**Manual Request Examples:**
- *"Refresh branch A and B worktrees to match development"*
- *"I need to reset my A and B worktrees to the latest development branch"*
- *"Remove and recreate worktrees A and B as fresh copies of development"*

### For Users: How to Request Claude Code Create a New Worktree

Instead of running bash commands manually, you can ask Claude Code to intelligently manage everything for you:

**Simple Request Examples:**
- *"Create a new worktree for working on user authentication improvements"*
- *"I need a separate environment to fix the search bug without affecting my current work"*
- *"Set up a worktree for experimenting with the new UI design"*
- *"Create a hotfix worktree from the main branch to address the production issue"*

**What Claude Code Will Do Automatically:**
1. **Analyze your request** to determine the appropriate worktree name and branch
2. **Create the worktree** using the automated setup script
3. **Set up the complete environment** (Python venv, Node modules, .env file)
4. **Verify the setup** and provide you with the path to navigate to
5. **Offer to start a new Claude session** in the worktree directory

**Advanced Requests:**
- *"Create a worktree from the development branch for the chat feature, and make sure it uses the staging database"*
- *"I need a worktree for testing approach A and another for approach B so I can compare implementations"*
- *"Set up a worktree for the urgent login fix and configure it to use production-like settings"*

**What You DON'T Need to Do:**
- Run any bash commands manually
- Remember script names or syntax
- Navigate directories or manage paths
- Set up Python virtual environments
- Install dependencies
- Copy configuration files
- Remember naming conventions

**Claude Code will handle all the technical details** and create a fully configured development environment ready for immediate use.

## Table of Contents
- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Detailed Setup](#detailed-setup)
- [Environment Management](#environment-management)
- [Claude Code Integration](#claude-code-integration)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)
- [Common Workflows](#common-workflows)

## Overview

Git worktrees allow you to check out multiple branches of the same repository into separate directories simultaneously. This is perfect for:
- Working on features while handling urgent bug fixes
- Testing different approaches in parallel
- Running multiple Claude Code sessions without conflicts
- Keeping production fixes separate from development work

### Project Structure with Worktrees
```
/Users/mitch/Documents/Projects/
├── mental-model/                 # Main worktree (development branch)
├── mental-model-feature-x/       # Feature branch worktree
├── mental-model-bugfix-123/      # Bug fix worktree
└── mental-model-production-fix/  # Production hotfix worktree
```

## Prerequisites

1. Git version 2.5 or higher (check with `git --version`)
2. Python 3.8+ with pip
3. Node.js 18+ with npm
4. Docker (for Neo4j database)
5. Environment variables file (.env)

## Quick Start

### Creating a New Worktree

```bash
# From your main project directory
cd /Users/mitch/Documents/Projects/mental-model

# Create a worktree for a new feature
git worktree add ../mental-model-feature-auth -b feature/auth-improvements

# Create a worktree from an existing branch
git worktree add ../mental-model-bugfix-search bugfix/search-issue
```

### Setting Up the New Worktree

```bash
# Navigate to the new worktree
cd ../mental-model-feature-auth

# Run the setup script (created in this guide)
./scripts/create-worktree.sh
```

## Detailed Setup

### Manual Environment Setup

When scripts aren't available, follow these steps:

#### 1. Backend (Python) Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
source venv/bin/activate  # On macOS/Linux
# OR
venv\Scripts\activate     # On Windows

# Install dependencies
pip install -r requirements.txt

# Copy environment variables
cp ../<main-worktree>/.env ../.env
```

#### 2. Frontend (React) Setup

```bash
cd frontend

# Install dependencies
npm install

# Build if needed
npm run build
```

#### 3. Git Hooks Setup

```bash
# From worktree root
./setup-hooks.sh
```

#### 4. Database Configuration

Each worktree can either:
- Share the same local Neo4j instance (recommended for most cases)
- Use a separate database name in the same instance
- Connect to different Neo4j instances (for isolation)

## Environment Management

### Python Virtual Environments

**IMPORTANT**: Each worktree MUST have its own Python virtual environment to avoid conflicts.

```bash
# Always create venv inside the worktree's backend directory
cd <worktree>/backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Node Modules

Each worktree maintains its own `node_modules`:

```bash
cd <worktree>/frontend
npm install
```

### Environment Variables

Options for managing `.env` files:

1. **Shared Configuration** (recommended for development):
   ```bash
   # Symlink to main worktree's .env
   ln -s /Users/mitch/Documents/Projects/mental-model/.env .env
   ```

2. **Isolated Configuration**:
   ```bash
   # Copy and modify as needed
   cp /Users/mitch/Documents/Projects/mental-model/.env .env
   # Edit .env for worktree-specific settings
   ```

## Claude Code Integration

### Starting Claude in a Worktree

```bash
# Navigate to the worktree
cd /Users/mitch/Documents/Projects/mental-model-feature-auth

# Start Claude Code
claude
```

### Instructions for Claude (Add to CLAUDE.md)

When working in a worktree, Claude should:

1. **Check Current Directory**: Always verify the worktree location with `pwd`
2. **Activate Virtual Environment**: Before running Python commands:
   ```bash
   cd backend && source venv/bin/activate
   ```
3. **Verify Branch**: Check current branch with `git branch --show-current`
4. **Environment Setup**: Ensure all dependencies are installed before running code

### Parallel Claude Sessions

You can run multiple Claude Code sessions simultaneously:

```bash
# Terminal 1 - Feature development
cd /Users/mitch/Documents/Projects/mental-model-feature-auth
claude

# Terminal 2 - Bug fix
cd /Users/mitch/Documents/Projects/mental-model-bugfix-search  
claude
```

## Best Practices

### 1. Naming Conventions

Use descriptive worktree names:
- `mental-model-feature-<name>` for features
- `mental-model-bugfix-<issue>` for bug fixes
- `mental-model-hotfix-<desc>` for production fixes
- `mental-model-experiment-<name>` for experiments

### 2. Branch Management

- Always create worktrees from up-to-date branches
- Pull latest changes before creating worktrees:
  ```bash
  git fetch origin
  git worktree add ../mental-model-feature-x origin/main -b feature/x
  ```

### 3. Resource Considerations

- Each worktree with dependencies uses ~500MB-1GB disk space
- Python venv: ~300-500MB
- Node modules: ~200-400MB
- Consider disk space when creating multiple worktrees

### 4. Cleanup

Remove worktrees when done:
```bash
# From any directory
git worktree remove /path/to/worktree

# Force removal if there are uncommitted changes
git worktree remove --force /path/to/worktree

# List all worktrees
git worktree list

# Prune stale worktree references
git worktree prune
```

## Troubleshooting

### Common Issues

#### 1. "fatal: '<branch>' is already checked out"
**Solution**: A branch can only be checked out in one worktree at a time. Use a different branch or create a new one.

#### 2. Python Import Errors
**Solution**: Ensure you've activated the correct virtual environment:
```bash
cd backend && source venv/bin/activate
```

#### 3. Node Module Conflicts
**Solution**: Clean install in the worktree:
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

#### 4. Database Connection Issues
**Solution**: Verify Neo4j is running and .env has correct credentials:
```bash
docker compose up -d  # Start Neo4j
```

#### 5. Git Hooks Not Running
**Solution**: Run setup script in the worktree:
```bash
./setup-hooks.sh
```

### Verification Steps

1. **Check Worktree Status**:
   ```bash
   git worktree list
   ```

2. **Verify Python Environment**:
   ```bash
   which python  # Should show venv path
   pip list     # Should show project dependencies
   ```

3. **Test Backend**:
   ```bash
   cd backend && python main.py
   # Should start on port 8000
   ```

4. **Test Frontend**:
   ```bash
   cd frontend && npm start
   # Should start on port 3000
   ```

## Worktree Refresh Workflow

### Refreshing Existing Worktrees to Match Development

When you need to reset existing worktrees to be fresh copies of the development branch:

```bash
# For each branch (A, B, etc.), run these commands:

# Remove existing worktree registration
git worktree remove --force ../branch-A

# Clean up directory if needed
rm -rf ../branch-A

# Delete the existing branch
git branch -D A

# Create fresh worktree with new branch based on development
git worktree add -b A ../branch-A development
```

**Automated Script Usage:**
```bash
# Use the custom slash command for multiple branches
/refresh-worktrees A B

# Or ask Claude directly
"Refresh worktrees A and B to match development branch"
```

**When to Use This Workflow:**
- After merging branches back to development
- When worktrees have diverged significantly from development
- To start fresh work based on latest development changes
- Before beginning new feature work in existing worktrees

**Verification:**
```bash
# Check all worktrees point to same development commit
git worktree list
# Should show same commit hash for development and refreshed branches
```

## Common Workflows

### Workflow 1: Feature Development

```bash
# 1. Create feature worktree
git worktree add ../mental-model-feature-chat -b feature/enhanced-chat

# 2. Setup environment
cd ../mental-model-feature-chat
./scripts/create-worktree.sh

# 3. Start development
claude

# 4. After completion, push and cleanup
git push -u origin feature/enhanced-chat
cd ..
git worktree remove mental-model-feature-chat
```

### Workflow 2: Emergency Hotfix

```bash
# 1. Create hotfix from main
git worktree add ../mental-model-hotfix main -b hotfix/critical-bug

# 2. Quick setup
cd ../mental-model-hotfix
cp ../mental-model/.env .env
cd backend && python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 3. Fix and test
claude

# 4. Merge and cleanup
git push origin hotfix/critical-bug
# Create PR, merge to main
git worktree remove ../mental-model-hotfix
```

### Workflow 3: Parallel Testing

```bash
# Test different approaches simultaneously
git worktree add ../mental-model-approach-1 -b test/approach-1
git worktree add ../mental-model-approach-2 -b test/approach-2

# Run Claude in each to implement different solutions
# Compare results and choose best approach
```

## Script Usage

### create-worktree.sh
```bash
./scripts/create-worktree.sh <worktree-name> [branch-name]
# Example: ./scripts/create-worktree.sh feature-auth feature/auth-improvements
```

### list-worktrees.sh
```bash
./scripts/list-worktrees.sh
# Shows all worktrees with their status
```

### remove-worktree.sh
```bash
./scripts/remove-worktree.sh <worktree-path>
# Example: ./scripts/remove-worktree.sh ../mental-model-feature-auth
```

## Security Considerations

1. **Never commit .env files**: Ensure .env is in .gitignore
2. **Separate credentials**: Use different API keys for development/production
3. **Clean up secrets**: Remove sensitive data before removing worktrees

## Tips for Success

1. **Start small**: Create one worktree first to get comfortable
2. **Document branch purpose**: Use descriptive branch names
3. **Regular cleanup**: Remove unused worktrees to save disk space
4. **Consistent setup**: Use scripts to ensure uniform environment setup
5. **Communicate**: If working in a team, communicate which branches are in worktrees

## Conclusion

Git worktrees provide powerful parallel development capabilities. Combined with Claude Code, they enable efficient multitasking without environment conflicts. Follow this guide to maintain clean, isolated development environments for each task.