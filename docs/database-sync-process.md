# Database Sync Process Documentation

## Overview

This document outlines the complete process for syncing changes from the local Neo4j database to the production AuraDB instance. The sync system provides a flexible, database-to-database synchronization that works with any local changes.

## System Architecture

### Components

1. **LocalDBExporter** - Exports complete local database structure
2. **AuraDBAnalyzer** - Analyzes current production database state
3. **SyncEngine** - Performs intelligent differential sync
4. **EmbeddingManager** - Handles embeddings efficiently with reuse
5. **SyncValidator** - Validates sync results and data integrity
6. **sync_to_auradb.py** - Main orchestrator script

### Key Features

- **Flexible**: Works with any local database changes (not limited to JSON imports)
- **Intelligent**: Only syncs differences, preserves existing data
- **Safe**: Dry-run mode for testing, comprehensive validation
- **Efficient**: Reuses existing embeddings to minimize API costs
- **Complete**: Syncs nodes, labels, properties, and all relationship types

## Quick Start

### Prerequisites

1. Ensure environment variables are set in `.env`:
   ```bash
   NEO4J_URI=neo4j+s://your-auradb-instance.databases.neo4j.io
   NEO4J_USERNAME=neo4j
   NEO4J_PASSWORD=your-auradb-password
   ANTHROPIC_API_KEY=your-anthropic-key
   COHERE_API_KEY=your-cohere-key
   ```

2. Local Neo4j Docker container is running:
   ```bash
   docker compose up
   ```

### Basic Sync Process

1. **Test with Dry Run** (recommended):
   ```bash
   cd backend
   python sync_to_auradb.py --dry-run
   ```

2. **Perform Live Sync**:
   ```bash
   cd backend
   python sync_to_auradb.py
   ```

## Detailed Usage

### Command Line Options

```bash
python sync_to_auradb.py [OPTIONS]

Options:
  --dry-run         Perform analysis without making changes
  --verbose, -v     Enable detailed logging
  --export-only     Only export local database, don't sync
  -h, --help        Show help message
```

### Examples

```bash
# Test sync with detailed logging
python sync_to_auradb.py --dry-run --verbose

# Export local database only
python sync_to_auradb.py --export-only

# Perform live sync with minimal output
python sync_to_auradb.py
```

## Sync Process Steps

### Step 1: Local Database Export
- Connects to local Neo4j instance
- Exports all nodes with labels, properties, and internal IDs
- Exports all relationships with types and properties
- Saves complete export to `../backups/sync_export_[timestamp].json`

### Step 2: AuraDB State Analysis
- Connects to production AuraDB instance
- Analyzes current nodes and relationships
- Builds comparison baseline
- Calculates differences requiring sync

### Step 3: Embedding Optimization
- Extracts existing embeddings from AuraDB
- Compares content hashes to detect changes
- Reuses existing embeddings where content unchanged
- Generates new embeddings only when needed

### Step 4: Differential Sync
- **Dry Run**: Analyzes what changes would be made
- **Live Sync**: Executes actual sync operations
- Creates/updates nodes with all labels and properties
- Creates missing relationships of all types
- Processes in batches for performance

### Step 5: Validation
- Compares final database states
- Validates data integrity (IDs, embeddings, relationships)
- Checks sample entities for accuracy
- Generates comprehensive validation report

## Output Files

All sync operations create timestamped files in the `backups/` directory:

- `sync_export_[timestamp].json` - Complete local database export
- `sync_report_[timestamp].json` - Sync operation summary
- `validation_report_[timestamp].json` - Post-sync validation results

## Data Types Synchronized

### Nodes
- **Entity nodes**: With all labels (Entity + Principle/Pattern/Example)
- **Theme nodes**: Categorization nodes
- **Properties**: All node properties including embeddings
- **Labels**: Multiple labels per node properly maintained

### Relationships
- **BELONGS_TO**: Entity to Theme connections
- **DEMONSTRATES**: Cross-entity demonstrations
- **EVIDENCED_BY**: Evidence relationships
- **MANIFESTS_AS**: Manifestation patterns
- **BUILDS_ON**: Dependency relationships
- **BALANCES**: Balance relationships
- **SUPPORTS**: Support relationships
- **CONTRADICTS**: Contradiction relationships

## Safety Features

### Pre-Sync Validation
- Verifies database connectivity
- Checks environment variables
- Validates local database integrity

### During Sync
- Batch processing prevents timeouts
- Rate limiting for API calls
- Error handling and retry logic
- Progress tracking and logging

### Post-Sync Validation
- Node count verification
- Relationship count verification
- Sample entity validation
- Data integrity checks
- Perfect sync confirmation

## Troubleshooting

### Common Issues

1. **Connection Failures**
   ```bash
   # Verify environment variables
   cat .env | grep NEO4J
   
   # Test AuraDB connection
   python debug_database_access.py
   ```

2. **Embedding Generation Errors**
   ```bash
   # Check Cohere API key
   python -c "import os; print(os.getenv('COHERE_API_KEY'))"
   
   # Test embedding generation
   python embedding_manager.py
   ```

3. **Sync Validation Failures**
   ```bash
   # Run standalone validation
   python sync_validator.py
   
   # Check specific entities
   python test_auradb_connection.py
   ```

### Error Recovery

1. **Partial Sync Failure**: Re-run the sync process - it's idempotent
2. **Validation Failure**: Check the validation report for specific issues
3. **Rate Limiting**: The system automatically handles rate limits with backoff

## Monitoring and Maintenance

### Regular Checks
- Monitor sync reports for trends
- Validate database integrity periodically
- Check embedding generation costs
- Review relationship sync completeness

### Performance Optimization
- Embedding reuse reduces API costs by ~90%
- Batch processing improves sync speed
- Differential sync minimizes unnecessary operations
- Constraint usage ensures data consistency

## Advanced Usage

### Standalone Component Usage

```bash
# Export local database only
python local_db_exporter.py

# Analyze AuraDB state
python auradb_analyzer.py

# Validate current sync state
python sync_validator.py

# Test embedding generation
python embedding_manager.py
```

### Custom Sync Scenarios

```python
# In Python script
from sync_to_auradb import SyncOrchestrator

# Create orchestrator
orchestrator = SyncOrchestrator(dry_run=True, verbose=True)

# Run specific steps
orchestrator.export_local_database()
orchestrator.analyze_auradb_current_state()
```

## Integration with Development Workflow

### Recommended Workflow

1. **Make changes to local database** (via import scripts, manual updates, etc.)
2. **Test sync with dry run**: `python sync_to_auradb.py --dry-run`
3. **Review sync analysis** to understand what will change
4. **Perform live sync**: `python sync_to_auradb.py`
5. **Verify results** in validation report
6. **Commit any code changes** related to the sync

### CI/CD Integration

The sync system can be integrated into automated workflows:

```bash
# In CI/CD pipeline
cd backend
python sync_to_auradb.py --dry-run  # Test sync
python sync_to_auradb.py            # Execute if dry run passes
```

## Best Practices

1. **Always dry run first** before live sync
2. **Monitor embedding costs** - reuse existing embeddings when possible
3. **Keep backups** of export files for recovery
4. **Validate results** after each sync
5. **Test locally** before syncing to production
6. **Document changes** that require special sync handling

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review sync reports and validation outputs
3. Run individual components for isolated testing
4. Check environment variable configuration
5. Verify local and production database connectivity

---

*Last updated: July 23, 2025*
*Sync system version: 1.0*