---
description: Refresh specified worktrees to match development branch
allowed-tools: Bash(git worktree:*), Bash(git branch:*), Bash(rm:*)
---

# Refresh Worktrees: $ARGUMENTS

Refresh the specified worktrees to be fresh copies of the development branch.

## Current Context

- Current branch: !`git branch --show-current`
- Existing worktrees: !`git worktree list`
- Development branch status: !`git log --oneline -3 development`

## Your Task

For each branch name in the arguments ($ARGUMENTS):

1. **Remove existing worktree**: Use `git worktree remove --force ../branch-{NAME}`
2. **Clean up directory**: Remove the directory with `rm -rf ../branch-{NAME}` if needed
3. **Delete existing branch**: Use `git branch -D {NAME}` 
4. **Create fresh worktree**: Use `git worktree add -b {NAME} ../branch-{NAME} development`
5. **Verify setup**: List final worktree status with `git worktree list`

Follow this exact pattern that was used successfully:

```bash
# For each branch (e.g., A, B):
git worktree remove --force ../branch-A
rm -rf ../branch-A  # if needed
git branch -D A
git worktree add -b A ../branch-A development
```

**Important**: Each branch should end up as a fresh copy of the current development branch state.

Verify all worktrees show the same commit hash as development when complete.