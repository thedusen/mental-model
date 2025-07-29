#!/bin/bash

# remove-worktree.sh - Safely remove a Git worktree with cleanup
# Usage: ./scripts/remove-worktree.sh <worktree-path> [--force]

set -e

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
    echo "Usage: $0 <worktree-path> [--force]"
    echo ""
    echo "Remove a Git worktree and clean up associated files"
    echo ""
    echo "Arguments:"
    echo "  worktree-path    Path to the worktree to remove"
    echo "  --force          Force removal even with uncommitted changes"
    echo ""
    echo "Examples:"
    echo "  $0 ../mental-model-feature-auth"
    echo "  $0 /Users/mitch/Documents/Projects/mental-model-bugfix-search"
    echo "  $0 ../mental-model-experiment-new-ui --force"
    echo ""
    exit 1
}

# Check arguments
if [ $# -lt 1 ] || [ $# -gt 2 ]; then
    usage
fi

WORKTREE_PATH="$1"
FORCE_REMOVAL=""

if [ "$2" = "--force" ]; then
    FORCE_REMOVAL="--force"
    print_warning "Force removal enabled - uncommitted changes will be lost"
fi

# Resolve absolute path
if [[ "$WORKTREE_PATH" != /* ]]; then
    WORKTREE_PATH="$(cd "$(dirname "$WORKTREE_PATH")" && pwd)/$(basename "$WORKTREE_PATH")"
fi

print_info "Removing worktree: $WORKTREE_PATH"

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    print_error "Not in a Git repository"
    exit 1
fi

# Check if worktree path exists
if [ ! -d "$WORKTREE_PATH" ]; then
    print_error "Worktree directory does not exist: $WORKTREE_PATH"
    
    # Check if it's a stale reference
    if git worktree list | grep -q "$WORKTREE_PATH"; then
        print_info "Found stale worktree reference. Pruning..."
        git worktree prune
        print_success "Stale references cleaned up"
    fi
    exit 1
fi

# Verify it's actually a worktree
if ! git worktree list | grep -q "$WORKTREE_PATH"; then
    print_error "Path is not a registered Git worktree: $WORKTREE_PATH"
    print_info "Use 'git worktree list' to see registered worktrees"
    exit 1
fi

# Get worktree information
WORKTREE_INFO=$(git worktree list --porcelain | grep -A 10 "worktree $WORKTREE_PATH")
BRANCH_NAME=$(echo "$WORKTREE_INFO" | grep "branch" | sed 's/branch refs\/heads\///' || echo "detached")

if [ "$BRANCH_NAME" = "detached" ]; then
    BRANCH_NAME="(detached HEAD)"
fi

print_info "Branch: $BRANCH_NAME"

# Change to worktree directory for checks
cd "$WORKTREE_PATH"

# Step 1: Check for uncommitted changes (unless forced)
if [ -z "$FORCE_REMOVAL" ]; then
    print_step "Checking for uncommitted changes"
    
    # Check for modified files
    if ! git diff-index --quiet HEAD -- 2>/dev/null; then
        print_error "Worktree has uncommitted changes"
        echo "Modified files:"
        git diff --name-only HEAD
        echo ""
        print_info "Options:"
        echo "  1. Commit your changes: git add . && git commit -m 'message'"
        echo "  2. Stash your changes: git stash"
        echo "  3. Force removal: $0 $1 --force"
        exit 1
    fi
    
    # Check for staged changes
    if ! git diff-index --quiet --cached HEAD -- 2>/dev/null; then
        print_error "Worktree has staged changes"
        echo "Staged files:"
        git diff --name-only --cached
        echo ""
        print_info "Options:"
        echo "  1. Commit staged changes: git commit -m 'message'"
        echo "  2. Unstage changes: git reset"
        echo "  3. Force removal: $0 $1 --force"
        exit 1
    fi
    
    # Check for untracked files
    UNTRACKED_FILES=$(git ls-files --others --exclude-standard)
    if [ -n "$UNTRACKED_FILES" ]; then
        print_warning "Worktree has untracked files:"
        echo "$UNTRACKED_FILES"
        echo ""
        read -p "Continue with removal? These files will be deleted. (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_info "Removal cancelled"
            exit 0
        fi
    fi
    
    print_success "No uncommitted changes found"
fi

# Step 2: Check if branch should be deleted
print_step "Checking branch status"

# Don't offer to delete main branches
PROTECTED_BRANCHES=("main" "master" "development" "develop")
SHOULD_DELETE_BRANCH=""

if [[ ! " ${PROTECTED_BRANCHES[@]} " =~ " ${BRANCH_NAME} " ]] && [ "$BRANCH_NAME" != "(detached HEAD)" ]; then
    # Check if branch exists on remote
    if git ls-remote --heads origin "$BRANCH_NAME" | grep -q "$BRANCH_NAME"; then
        print_info "Branch '$BRANCH_NAME' exists on remote"
        read -p "Delete local branch '$BRANCH_NAME' after removing worktree? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            SHOULD_DELETE_BRANCH="yes"
        fi
    else
        print_warning "Branch '$BRANCH_NAME' is local-only"
        read -p "Delete local branch '$BRANCH_NAME' after removing worktree? (Y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Nn]$ ]]; then
            SHOULD_DELETE_BRANCH="yes"
        fi
    fi
else
    print_info "Protected branch '$BRANCH_NAME' will not be deleted"
fi

# Step 3: Display cleanup summary
print_step "Cleanup Summary"

echo "The following will be removed:"
echo "  • Worktree directory: $WORKTREE_PATH"
echo "  • Python virtual environment: backend/venv/"
echo "  • Node modules: frontend/node_modules/"
echo "  • Environment file: .env (if present)"

if [ "$SHOULD_DELETE_BRANCH" = "yes" ]; then
    echo "  • Local branch: $BRANCH_NAME"
fi

# Calculate disk space to be freed
if command -v du >/dev/null 2>&1; then
    DISK_USAGE=$(du -sh "$WORKTREE_PATH" 2>/dev/null | cut -f1 || echo "Unknown")
    echo "  • Disk space freed: ~$DISK_USAGE"
fi

echo ""
read -p "Proceed with removal? (y/N): " -n 1 -r
echo

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_info "Removal cancelled"
    exit 0
fi

# Step 4: Remove the worktree
print_step "Removing worktree"

# Go back to main repo to run git worktree remove
cd - > /dev/null

if [ -n "$FORCE_REMOVAL" ]; then
    git worktree remove "$WORKTREE_PATH" --force
else
    git worktree remove "$WORKTREE_PATH"
fi

print_success "Worktree removed: $WORKTREE_PATH"

# Step 5: Delete branch if requested
if [ "$SHOULD_DELETE_BRANCH" = "yes" ]; then
    print_step "Deleting branch"
    
    if git branch -d "$BRANCH_NAME" 2>/dev/null; then
        print_success "Branch deleted: $BRANCH_NAME"
    else
        print_warning "Could not delete branch '$BRANCH_NAME' - it may have unmerged changes"
        print_info "To force delete: git branch -D $BRANCH_NAME"
    fi
fi

# Step 6: Clean up any stale references
print_step "Cleaning up"

git worktree prune
print_success "Stale worktree references cleaned up"

# Step 7: Final summary
print_step "Removal Complete!"

echo ""
print_success "Worktree successfully removed"
print_info "Summary:"
echo "  • Removed: $WORKTREE_PATH"
if [ "$SHOULD_DELETE_BRANCH" = "yes" ]; then
    echo "  • Branch: $BRANCH_NAME (deleted)"
else
    echo "  • Branch: $BRANCH_NAME (preserved)"
fi

# Show remaining worktrees
REMAINING_WORKTREES=$(git worktree list | wc -l)
print_info "Remaining worktrees: $((REMAINING_WORKTREES - 1))"

if [ $REMAINING_WORKTREES -gt 1 ]; then
    echo ""
    print_info "To see remaining worktrees: ./scripts/list-worktrees.sh"
fi

echo ""