#!/usr/bin/env python3
"""
Analyze the differences between local and AuraDB node counts
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


def analyze_database(uri, username, password, name):
    """Analyze node types and counts in a database"""
    try:
        driver = GraphDatabase.driver(uri, auth=(username, password))
        with driver.session() as session:
            # Get all node labels and their counts
            result = session.run(
                """
                CALL db.labels() YIELD label
                CALL apoc.cypher.run('MATCH (n:`' + label + '`) RETURN count(n) as count', {}) 
                YIELD value
                RETURN label, value.count as count
                ORDER BY value.count DESC
            """
            )

            labels_counts = [(record["label"], record["count"]) for record in result]

            logger.info(f"📊 {name} Node Label Analysis:")
            total_labeled = 0
            for label, count in labels_counts:
                logger.info(f"  {label}: {count} nodes")
                total_labeled += count

            # Check for unlabeled nodes
            total_nodes = session.run("MATCH (n) RETURN count(n) as count").single()[
                "count"
            ]
            unlabeled = total_nodes - total_labeled

            logger.info(f"  Total labeled nodes: {total_labeled}")
            logger.info(f"  Total nodes: {total_nodes}")
            if unlabeled > 0:
                logger.info(f"  ⚠️  Unlabeled nodes: {unlabeled}")

            return {
                "labels_counts": labels_counts,
                "total_nodes": total_nodes,
                "total_labeled": total_labeled,
                "unlabeled": unlabeled,
            }

    except Exception as e:
        logger.error(f"❌ Error analyzing {name}: {str(e)}")
        # Try without APOC
        try:
            with driver.session() as session:
                # Basic analysis without APOC
                entity_count = session.run(
                    "MATCH (n:Entity) RETURN count(n) as count"
                ).single()["count"]
                theme_count = session.run(
                    "MATCH (n:Theme) RETURN count(n) as count"
                ).single()["count"]
                total_nodes = session.run(
                    "MATCH (n) RETURN count(n) as count"
                ).single()["count"]

                logger.info(f"📊 {name} Basic Analysis (APOC not available):")
                logger.info(f"  Entity: {entity_count} nodes")
                logger.info(f"  Theme: {theme_count} nodes")
                logger.info(f"  Total nodes: {total_nodes}")
                logger.info(
                    f"  Other nodes: {total_nodes - entity_count - theme_count}"
                )

                return {
                    "labels_counts": [("Entity", entity_count), ("Theme", theme_count)],
                    "total_nodes": total_nodes,
                    "other_nodes": total_nodes - entity_count - theme_count,
                }
        except Exception as e2:
            logger.error(f"❌ Fallback analysis also failed for {name}: {str(e2)}")
            return None
    finally:
        if "driver" in locals():
            driver.close()


def main():
    # Connection details
    local_uri = "bolt://localhost:7687"
    local_username = os.getenv("NEO4J_USERNAME", "neo4j")
    local_password = os.getenv("NEO4J_PASSWORD", "password123")

    aura_uri = os.getenv("NEO4J_URI")
    aura_username = os.getenv("NEO4J_USERNAME")
    aura_password = os.getenv("NEO4J_PASSWORD")

    logger.info("🔍 Analyzing node differences between LOCAL and AuraDB")

    local_analysis = analyze_database(
        local_uri, local_username, local_password, "LOCAL"
    )
    aura_analysis = analyze_database(aura_uri, aura_username, aura_password, "AuraDB")

    if local_analysis and aura_analysis:
        logger.info("🔍 DIFFERENCE ANALYSIS:")
        node_diff = local_analysis["total_nodes"] - aura_analysis["total_nodes"]
        logger.info(f"Local has {node_diff} more nodes than AuraDB")

        if "other_nodes" in local_analysis and "other_nodes" in aura_analysis:
            other_diff = local_analysis["other_nodes"] - aura_analysis["other_nodes"]
            logger.info(f"Difference in 'other' nodes: {other_diff}")


if __name__ == "__main__":
    main()
