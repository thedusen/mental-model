# Mental Model

A Neo4j-based knowledge graph system for building and exploring mental models.

[![GitHub](https://img.shields.io/badge/GitHub-thedusen/mental--model-blue?logo=github)](https://github.com/thedusen/mental-model)

## Quick Start

1. **Launch Neo4j database:**
   ```bash
   docker compose up
   ```

2. **Access Neo4j Browser:**
   - Open your browser to [http://localhost:7474](http://localhost:7474)
   - Login with username: `neo4j`, password: `password123`

3. **Connect via Bolt protocol:**
   - Use `bolt://localhost:7687` for programmatic access

## Project Structure

```
mental-model/
├── docker-compose.yml    # Neo4j service configuration
├── neo4j/               # Neo4j data and logs
│   ├── data/           # Database files (created on first run)
│   └── logs/           # Neo4j log files
│       ├── debug.log
│       ├── http.log
│       ├── neo4j.log
│       ├── query.log
│       └── security.log
└── README.md           # This file
```

### Key Components

- **docker-compose.yml**: Configures Neo4j 5.25.1 with APOC plugin enabled
- **neo4j/**: Volume-mounted directory for persistent data and logs
- **Ports**: 7474 (Browser UI), 7687 (Bolt protocol)

## Development

### Using Cursor IDE

For enhanced development experience with Cursor IDE:
- [Cursor IDE Documentation](https://docs.cursor.sh/)
- [Cursor IDE Getting Started](https://docs.cursor.sh/getting-started/installation)

### Neo4j Resources

- [Neo4j Documentation](https://neo4j.com/docs/)
- [Cypher Query Language](https://neo4j.com/docs/cypher-manual/current/)
- [APOC Procedures](https://neo4j.com/docs/apoc/current/)

## Stopping the Database

```bash
docker compose down
```

To remove all data and start fresh:
```bash
docker compose down -v
```
# Test PR
