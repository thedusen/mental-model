#!/usr/bin/env python3
"""
Analyze the complete structure of the local database to understand all data types,
relationships, and what needs to be synced to AuraDB.
"""
import os
from dotenv import load_dotenv
from neo4j import GraphDatabase
import logging

load_dotenv(override=True)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def analyze_complete_structure():
    """Analyze the complete structure of the local database"""
    local_uri = "bolt://localhost:7687"
    local_username = os.getenv("NEO4J_USERNAME", "neo4j")
    local_password = os.getenv("NEO4J_PASSWORD", "password123")

    try:
        driver = GraphDatabase.driver(local_uri, auth=(local_username, local_password))
        with driver.session() as session:
            logger.info("🔍 ANALYZING LOCAL DATABASE STRUCTURE")

            # Get all node labels and counts
            logger.info("\n📊 NODE LABELS AND COUNTS:")
            try:
                # Try with APOC first
                result = session.run(
                    """
                    CALL db.labels() YIELD label
                    CALL apoc.cypher.run('MATCH (n:`' + label + '`) RETURN count(n) as count', {}) 
                    YIELD value
                    RETURN label, value.count as count
                    ORDER BY value.count DESC
                """
                )
                for record in result:
                    logger.info(f"  {record['label']}: {record['count']} nodes")
            except:
                # Fallback without APOC
                labels = session.run("CALL db.labels()").values()
                for label_record in labels:
                    label = label_record[0]
                    count = session.run(
                        f"MATCH (n:`{label}`) RETURN count(n) as count"
                    ).single()["count"]
                    logger.info(f"  {label}: {count} nodes")

            # Get all relationship types and counts
            logger.info("\n🔗 RELATIONSHIP TYPES AND COUNTS:")
            try:
                result = session.run(
                    """
                    CALL db.relationshipTypes() YIELD relationshipType
                    CALL apoc.cypher.run('MATCH ()-[r:`' + relationshipType + '`]->() RETURN count(r) as count', {}) 
                    YIELD value
                    RETURN relationshipType, value.count as count
                    ORDER BY value.count DESC
                """
                )
                for record in result:
                    logger.info(
                        f"  {record['relationshipType']}: {record['count']} relationships"
                    )
            except:
                # Fallback without APOC
                rel_types = session.run("CALL db.relationshipTypes()").values()
                for rel_record in rel_types:
                    rel_type = rel_record[0]
                    count = session.run(
                        f"MATCH ()-[r:`{rel_type}`]->() RETURN count(r) as count"
                    ).single()["count"]
                    logger.info(f"  {rel_type}: {count} relationships")

            # Sample nodes with multiple labels
            logger.info("\n🏷️  SAMPLE NODES WITH MULTIPLE LABELS:")
            result = session.run(
                """
                MATCH (n)
                WHERE size(labels(n)) > 1
                RETURN labels(n) as labels, n.id as id
                LIMIT 10
            """
            )
            for record in result:
                logger.info(f"  {record['id']}: {record['labels']}")

            # Sample relationships patterns
            logger.info("\n🔄 SAMPLE RELATIONSHIP PATTERNS:")
            result = session.run(
                """
                MATCH (a)-[r]->(b)
                RETURN DISTINCT labels(a)[0] as from_label, type(r) as rel_type, labels(b)[0] as to_label
                LIMIT 20
            """
            )
            for record in result:
                logger.info(
                    f"  ({record['from_label']})-[:{record['rel_type']}]->({record['to_label']})"
                )

            # Check for entity-to-entity relationships (not just theme relationships)
            logger.info("\n🔗 ENTITY-TO-ENTITY RELATIONSHIPS:")
            result = session.run(
                """
                MATCH (e1:Entity)-[r]->(e2:Entity)
                RETURN type(r) as rel_type, count(*) as count
                ORDER BY count DESC
            """
            )
            for record in result:
                logger.info(
                    f"  {record['rel_type']}: {record['count']} Entity->Entity relationships"
                )

            # Check properties on entities
            logger.info("\n📋 SAMPLE ENTITY PROPERTIES:")
            result = session.run(
                """
                MATCH (e:Entity)
                RETURN e.id as id, labels(e) as labels, keys(e) as properties
                LIMIT 5
            """
            )
            for record in result:
                logger.info(
                    f"  {record['id']}: {record['labels']} -> {record['properties']}"
                )

    except Exception as e:
        logger.error(f"❌ Error analyzing database: {str(e)}")
    finally:
        if "driver" in locals():
            driver.close()


if __name__ == "__main__":
    analyze_complete_structure()
