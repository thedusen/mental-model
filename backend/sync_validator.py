#!/usr/bin/env python3
"""
SyncValidator - Validates sync results and ensures data integrity
Compares before/after states and verifies complete synchronization
"""
import os
from datetime import datetime
from dotenv import load_dotenv
from neo4j import GraphDatabase
import logging

load_dotenv(override=True)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class SyncValidator:
    def __init__(self):
        self.local_uri = "bolt://localhost:7687"
        self.local_username = os.getenv("NEO4J_USERNAME", "neo4j")
        self.local_password = os.getenv("NEO4J_PASSWORD", "password123")

        self.aura_uri = os.getenv("NEO4J_URI")
        self.aura_username = os.getenv("NEO4J_USERNAME")
        self.aura_password = os.getenv("NEO4J_PASSWORD")

        if not all([self.aura_uri, self.aura_username, self.aura_password]):
            raise ValueError("Missing AuraDB credentials in environment variables")

    def get_database_stats(self, uri, username, password, db_name):
        """Get comprehensive statistics from a database"""
        try:
            driver = GraphDatabase.driver(uri, auth=(username, password))
            with driver.session() as session:
                # Basic counts
                node_count = session.run("MATCH (n) RETURN count(n) as count").single()[
                    "count"
                ]
                rel_count = session.run(
                    "MATCH ()-[r]->() RETURN count(r) as count"
                ).single()["count"]

                # Label counts
                label_counts = {}
                labels_result = session.run("CALL db.labels()").values()
                for label_record in labels_result:
                    label = label_record[0]
                    count = session.run(
                        f"MATCH (n:`{label}`) RETURN count(n) as count"
                    ).single()["count"]
                    label_counts[label] = count

                # Relationship type counts
                rel_type_counts = {}
                rel_types_result = session.run("CALL db.relationshipTypes()").values()
                for rel_type_record in rel_types_result:
                    rel_type = rel_type_record[0]
                    count = session.run(
                        f"MATCH ()-[r:`{rel_type}`]->() RETURN count(r) as count"
                    ).single()["count"]
                    rel_type_counts[rel_type] = count

                # Entity-specific stats
                entity_count = session.run(
                    "MATCH (n:Entity) RETURN count(n) as count"
                ).single()["count"]
                entities_with_embeddings = session.run(
                    "MATCH (n:Entity) WHERE n.embedding IS NOT NULL RETURN count(n) as count"
                ).single()["count"]
                theme_count = session.run(
                    "MATCH (n:Theme) RETURN count(n) as count"
                ).single()["count"]

                return {
                    "database": db_name,
                    "timestamp": datetime.now().isoformat(),
                    "total_nodes": node_count,
                    "total_relationships": rel_count,
                    "label_counts": label_counts,
                    "relationship_type_counts": rel_type_counts,
                    "entity_count": entity_count,
                    "entities_with_embeddings": entities_with_embeddings,
                    "theme_count": theme_count,
                }

        except Exception as e:
            logger.error(f"❌ Failed to get stats from {db_name}: {str(e)}")
            return None
        finally:
            if "driver" in locals():
                driver.close()

    def validate_data_integrity(self, uri, username, password, db_name):
        """Validate data integrity in a database"""
        logger.info(f"🔍 Validating data integrity in {db_name}...")

        issues = []

        try:
            driver = GraphDatabase.driver(uri, auth=(username, password))
            with driver.session() as session:
                # Check for entities without IDs
                result = session.run(
                    "MATCH (n:Entity) WHERE n.id IS NULL RETURN count(n) as count"
                ).single()
                entities_without_ids = result["count"]
                if entities_without_ids > 0:
                    issues.append(
                        f"❌ {entities_without_ids} entities without ID property"
                    )

                # Check for entities without embeddings
                result = session.run(
                    "MATCH (n:Entity) WHERE n.embedding IS NULL RETURN count(n) as count"
                ).single()
                entities_without_embeddings = result["count"]
                if entities_without_embeddings > 0:
                    issues.append(
                        f"⚠️ {entities_without_embeddings} entities without embeddings"
                    )

                # Check for orphaned entities (no theme relationship)
                result = session.run(
                    "MATCH (n:Entity) WHERE NOT (n)-[:BELONGS_TO]->(:Theme) RETURN count(n) as count"
                ).single()
                orphaned_entities = result["count"]
                if orphaned_entities > 0:
                    issues.append(
                        f"⚠️ {orphaned_entities} entities not connected to themes"
                    )

                # Check for themes without entities
                result = session.run(
                    "MATCH (t:Theme) WHERE NOT (:Entity)-[:BELONGS_TO]->(t) RETURN count(t) as count"
                ).single()
                empty_themes = result["count"]
                if empty_themes > 0:
                    issues.append(f"⚠️ {empty_themes} themes with no entities")

                # Check for duplicate entity IDs
                result = session.run(
                    """
                    MATCH (n:Entity)
                    WITH n.id as entity_id, count(*) as count
                    WHERE count > 1
                    RETURN count(*) as duplicate_count
                """
                ).single()
                duplicate_ids = result["duplicate_count"]
                if duplicate_ids > 0:
                    issues.append(f"❌ {duplicate_ids} duplicate entity IDs found")

                # Check embedding dimensions
                result = session.run(
                    """
                    MATCH (n:Entity) 
                    WHERE n.embedding IS NOT NULL 
                    AND size(n.embedding) <> 1024
                    RETURN count(n) as count
                """
                ).single()
                invalid_embeddings = result["count"]
                if invalid_embeddings > 0:
                    issues.append(
                        f"❌ {invalid_embeddings} entities with invalid embedding dimensions"
                    )

        except Exception as e:
            issues.append(f"❌ Validation error: {str(e)}")
        finally:
            if "driver" in locals():
                driver.close()

        if not issues:
            logger.info(f"✅ {db_name} data integrity validation passed")
        else:
            logger.warning(f"⚠️ {db_name} data integrity issues found:")
            for issue in issues:
                logger.warning(f"   {issue}")

        return issues

    def compare_databases(self, pre_sync_aura_stats=None):
        """Compare local and AuraDB databases"""
        logger.info("🔍 Comparing local and AuraDB databases...")

        # Get current stats
        local_stats = self.get_database_stats(
            self.local_uri, self.local_username, self.local_password, "LOCAL"
        )
        aura_stats = self.get_database_stats(
            self.aura_uri, self.aura_username, self.aura_password, "AuraDB"
        )

        if not local_stats or not aura_stats:
            logger.error("❌ Failed to get database statistics")
            return None

        comparison = {
            "timestamp": datetime.now().isoformat(),
            "local_stats": local_stats,
            "aura_stats": aura_stats,
            "pre_sync_aura_stats": pre_sync_aura_stats,
            "differences": {},
            "sync_effectiveness": {},
        }

        # Calculate differences
        comparison["differences"] = {
            "node_count_diff": local_stats["total_nodes"] - aura_stats["total_nodes"],
            "rel_count_diff": local_stats["total_relationships"]
            - aura_stats["total_relationships"],
            "entity_count_diff": local_stats["entity_count"]
            - aura_stats["entity_count"],
            "embedding_count_diff": local_stats["entities_with_embeddings"]
            - aura_stats["entities_with_embeddings"],
            "theme_count_diff": local_stats["theme_count"] - aura_stats["theme_count"],
        }

        # Calculate sync effectiveness if we have pre-sync stats
        if pre_sync_aura_stats:
            comparison["sync_effectiveness"] = {
                "nodes_synced": aura_stats["total_nodes"]
                - pre_sync_aura_stats["total_nodes"],
                "relationships_synced": aura_stats["total_relationships"]
                - pre_sync_aura_stats["total_relationships"],
                "entities_synced": aura_stats["entity_count"]
                - pre_sync_aura_stats["entity_count"],
                "embeddings_synced": aura_stats["entities_with_embeddings"]
                - pre_sync_aura_stats["entities_with_embeddings"],
            }

        # Log comparison results
        logger.info("📊 Database comparison results:")
        logger.info(
            f"   LOCAL:  {local_stats['total_nodes']} nodes, {local_stats['total_relationships']} relationships"
        )
        logger.info(
            f"   AuraDB: {aura_stats['total_nodes']} nodes, {aura_stats['total_relationships']} relationships"
        )
        logger.info(
            f"   Differences: {comparison['differences']['node_count_diff']} nodes, {comparison['differences']['rel_count_diff']} relationships"
        )

        # Determine sync status
        perfect_sync = all(diff == 0 for diff in comparison["differences"].values())
        if perfect_sync:
            logger.info("✅ Perfect synchronization achieved!")
        else:
            logger.warning("⚠️ Databases are not perfectly synchronized")

        comparison["perfect_sync"] = perfect_sync

        return comparison

    def validate_specific_entities(self, sample_entity_ids):
        """Validate specific entities exist in both databases with same data"""
        logger.info(f"🔍 Validating {len(sample_entity_ids)} specific entities...")

        validation_results = {
            "matches": 0,
            "mismatches": 0,
            "missing_in_aura": 0,
            "details": [],
        }

        try:
            # Connect to both databases
            local_driver = GraphDatabase.driver(
                self.local_uri, auth=(self.local_username, self.local_password)
            )
            aura_driver = GraphDatabase.driver(
                self.aura_uri, auth=(self.aura_username, self.aura_password)
            )

            for entity_id in sample_entity_ids:
                # Get entity from local
                with local_driver.session() as session:
                    local_result = session.run(
                        "MATCH (n:Entity {id: $id}) RETURN labels(n) as labels, properties(n) as props",
                        id=entity_id,
                    ).single()

                # Get entity from AuraDB
                with aura_driver.session() as session:
                    aura_result = session.run(
                        "MATCH (n:Entity {id: $id}) RETURN labels(n) as labels, properties(n) as props",
                        id=entity_id,
                    ).single()

                if not aura_result:
                    validation_results["missing_in_aura"] += 1
                    validation_results["details"].append(
                        f"❌ {entity_id}: Missing in AuraDB"
                    )
                elif local_result and aura_result:
                    # Compare labels
                    local_labels = set(local_result["labels"])
                    aura_labels = set(aura_result["labels"])

                    if local_labels == aura_labels:
                        validation_results["matches"] += 1
                        validation_results["details"].append(
                            f"✅ {entity_id}: Labels match"
                        )
                    else:
                        validation_results["mismatches"] += 1
                        validation_results["details"].append(
                            f"⚠️ {entity_id}: Label mismatch - Local: {local_labels}, AuraDB: {aura_labels}"
                        )

        except Exception as e:
            logger.error(f"❌ Entity validation failed: {str(e)}")
        finally:
            if "local_driver" in locals():
                local_driver.close()
            if "aura_driver" in locals():
                aura_driver.close()

        logger.info(
            f"📊 Entity validation: {validation_results['matches']} matches, {validation_results['mismatches']} mismatches, {validation_results['missing_in_aura']} missing"
        )

        return validation_results

    def perform_complete_validation(
        self, pre_sync_aura_stats=None, sample_entities=None
    ):
        """Perform complete validation of sync results"""
        logger.info("🧪 Performing complete sync validation...")

        validation_report = {
            "timestamp": datetime.now().isoformat(),
            "database_comparison": None,
            "local_integrity": None,
            "aura_integrity": None,
            "entity_validation": None,
            "overall_status": "UNKNOWN",
        }

        # Compare databases
        validation_report["database_comparison"] = self.compare_databases(
            pre_sync_aura_stats
        )

        # Validate data integrity
        validation_report["local_integrity"] = self.validate_data_integrity(
            self.local_uri, self.local_username, self.local_password, "LOCAL"
        )
        validation_report["aura_integrity"] = self.validate_data_integrity(
            self.aura_uri, self.aura_username, self.aura_password, "AuraDB"
        )

        # Validate specific entities if provided
        if sample_entities:
            validation_report["entity_validation"] = self.validate_specific_entities(
                sample_entities
            )

        # Determine overall status
        perfect_sync = (
            validation_report["database_comparison"]["perfect_sync"]
            if validation_report["database_comparison"]
            else False
        )
        no_integrity_issues = (
            len(validation_report["local_integrity"]) == 0
            and len(validation_report["aura_integrity"]) == 0
        )

        if perfect_sync and no_integrity_issues:
            validation_report["overall_status"] = "SUCCESS"
            logger.info("✅ VALIDATION PASSED: Sync completed successfully!")
        elif perfect_sync:
            validation_report["overall_status"] = "SUCCESS_WITH_WARNINGS"
            logger.warning(
                "⚠️ VALIDATION PASSED WITH WARNINGS: Sync completed but integrity issues found"
            )
        else:
            validation_report["overall_status"] = "FAILED"
            logger.error("❌ VALIDATION FAILED: Sync incomplete or failed")

        return validation_report


def main():
    """Main function for standalone validation"""
    validator = SyncValidator()

    # Perform validation
    report = validator.perform_complete_validation()

    print(f"Validation Status: {report['overall_status']}")
    if report["database_comparison"]:
        print(f"Perfect Sync: {report['database_comparison']['perfect_sync']}")


if __name__ == "__main__":
    main()
