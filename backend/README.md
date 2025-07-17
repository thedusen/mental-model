# Backend - Mental Model

This is the backend service for the Mental Model application.

## Development Setup

### Dependencies

This project uses `pip-tools` for dependency management to ensure consistent versions across environments.

**Files:**
- `requirements.in` - Source dependencies (what you edit)
- `requirements.lock` - Pinned versions (auto-generated, committed to git)
- `requirements.txt` - Legacy file (kept for backwards compatibility)

### Installation

1. Install dependencies:
   ```bash
   pip install -r requirements.lock
   ```

2. Install pip-tools (if not already installed):
   ```bash
   pip install pip-tools
   ```

### Adding New Dependencies

1. Add the new dependency to `requirements.in`
2. Regenerate the lock file:
   ```bash
   pip-compile requirements.in --output-file requirements.lock
   ```
3. Install the new dependencies:
   ```bash
   pip install -r requirements.lock
   ```
4. Commit both files:
   ```bash
   git add requirements.in requirements.lock
   git commit -m "Add new dependency: package-name"
   ```

### Updating Dependencies

To update all dependencies to their latest compatible versions:
```bash
pip-compile --upgrade requirements.in --output-file requirements.lock
pip install -r requirements.lock
```

## Running the Application

```bash
uvicorn main:app --reload
```
