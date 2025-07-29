#!/bin/bash

# list-worktrees.sh - Display all Git worktrees with detailed status
# Usage: ./scripts/list-worktrees.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Helper functions
print_header() {
    echo -e "${BLUE}$1${NC}"
}

print_worktree() {
    echo -e "${GREEN}$1${NC}"
}

print_branch() {
    echo -e "${CYAN}$1${NC}"
}

print_status() {
    echo -e "${YELLOW}$1${NC}"
}

print_info() {
    echo -e "${PURPLE}$1${NC}"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to display individual worktree information
display_worktree_info() {
    local worktree_path="$1"
    local head_commit="$2"
    local branch_name="$3"
    
    # Determine if this is the main worktree
    local is_main=""
    if [ "$(basename "$worktree_path")" = "mental-model" ]; then
        is_main=" (main)"
    fi
    
    print_worktree "Worktree: $(basename "$worktree_path")$is_main"
    print_info "  Path: $worktree_path"
    print_branch "  Branch: $branch_name"
    
    # Check if worktree directory exists
    if [ ! -d "$worktree_path" ]; then
        print_error "  Status: Directory missing - run 'git worktree prune'"
        return
    fi
    
    # Get git status for the worktree
    local git_status=""
    if [ -d "$worktree_path/.git" ] || [ -f "$worktree_path/.git" ]; then
        local current_dir=$(pwd)
        cd "$worktree_path" 2>/dev/null || return
        
        # Check for uncommitted changes
        if ! git diff-index --quiet HEAD -- 2>/dev/null; then
            git_status="${git_status}modified files, "
        fi
        
        # Check for staged changes
        if ! git diff-index --quiet --cached HEAD -- 2>/dev/null; then
            git_status="${git_status}staged changes, "
        fi
        
        # Check for untracked files
        if [ -n "$(git ls-files --others --exclude-standard)" ]; then
            git_status="${git_status}untracked files, "
        fi
        
        # Clean up trailing comma
        git_status=${git_status%, }
        
        if [ -z "$git_status" ]; then
            git_status="clean"
        fi
        
        print_status "  Status: $git_status"
        
        # Check for environment setup
        check_environment_setup "$worktree_path"
        
        cd "$current_dir"
    else
        print_error "  Status: Invalid git worktree"
    fi
}

# Function to check environment setup
check_environment_setup() {
    local worktree_path="$1"
    local env_status=""
    
    # Check Python virtual environment
    if [ -d "$worktree_path/backend/venv" ]; then
        env_status="${env_status}Python venv ✓, "
    else
        env_status="${env_status}Python venv ✗, "
    fi
    
    # Check Node modules
    if [ -d "$worktree_path/frontend/node_modules" ]; then
        env_status="${env_status}Node modules ✓, "
    else
        env_status="${env_status}Node modules ✗, "
    fi
    
    # Check environment file
    if [ -f "$worktree_path/.env" ]; then
        env_status="${env_status}.env ✓"
    else
        env_status="${env_status}.env ✗"
    fi
    
    print_info "  Environment: $env_status"
    
    # Disk usage
    if command -v du >/dev/null 2>&1; then
        local size=$(du -sh "$worktree_path" 2>/dev/null | cut -f1 || echo "N/A")
        print_info "  Size: $size"
    fi
}

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    print_error "Not in a Git repository"
    exit 1
fi

# Header
echo
print_header "=== Git Worktrees Overview ==="
echo

# Get worktree list
WORKTREE_LIST=$(git worktree list --porcelain)

if [ -z "$WORKTREE_LIST" ]; then
    print_warning "No worktrees found"
    exit 0
fi

# Parse and display worktrees
WORKTREE_COUNT=0
CURRENT_WORKTREE=""
CURRENT_HEAD=""
CURRENT_BRANCH=""

while IFS= read -r line; do
    if [[ $line == worktree* ]]; then
        # If we have a previous worktree, display it
        if [ -n "$CURRENT_WORKTREE" ]; then
            display_worktree_info "$CURRENT_WORKTREE" "$CURRENT_HEAD" "$CURRENT_BRANCH"
            echo
        fi
        
        # Start new worktree
        CURRENT_WORKTREE=$(echo "$line" | cut -d' ' -f2)
        CURRENT_HEAD=""
        CURRENT_BRANCH=""
        WORKTREE_COUNT=$((WORKTREE_COUNT + 1))
        
    elif [[ $line == HEAD* ]]; then
        CURRENT_HEAD=$(echo "$line" | cut -d' ' -f2)
        
    elif [[ $line == branch* ]]; then
        CURRENT_BRANCH=$(echo "$line" | cut -d' ' -f2 | sed 's|refs/heads/||')
        
    elif [[ $line == detached ]]; then
        CURRENT_BRANCH="(detached HEAD)"
    fi
done <<< "$WORKTREE_LIST"

# Display the last worktree
if [ -n "$CURRENT_WORKTREE" ]; then
    display_worktree_info "$CURRENT_WORKTREE" "$CURRENT_HEAD" "$CURRENT_BRANCH"
fi


echo
print_header "=== Summary ==="
echo "Total worktrees: $WORKTREE_COUNT"

# Show useful commands
echo
print_header "=== Useful Commands ==="
echo "• Create worktree:   ./scripts/create-worktree.sh <name> [branch]"
echo "• Remove worktree:   ./scripts/remove-worktree.sh <path>"
echo "• Remove worktree:   git worktree remove <path>"
echo "• Prune invalid:     git worktree prune"
echo "• Start Claude:      cd <worktree-path> && claude"
echo

# Check for stale worktree references
STALE_REFS=$(git worktree list --porcelain | grep -E '^worktree' | cut -d' ' -f2 | while read -r path; do
    if [ ! -d "$path" ]; then
        echo "$path"
    fi
done)

if [ -n "$STALE_REFS" ]; then
    echo
    print_warning "Stale worktree references found. Run 'git worktree prune' to clean up:"
    echo "$STALE_REFS" | while read -r path; do
        echo "  - $path"
    done
fi