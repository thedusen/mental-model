#!/usr/bin/env python3
"""
Debug version of import_data.py with verbose logging to identify AuraDB import issues
"""
import os
import json
from config import cohere_client, get_db_session
from cohere.errors import TooManyRequestsError
import time
import logging

# Setup detailed logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

JSON_INPUT_PATH = "../data/themed_json"


def generate_embedding(text):
    """Generates an embedding for a given text using Cohere, with retry logic."""
    logger.debug(f"Generating embedding for text: {text[:100]}...")
    while True:
        try:
            response = cohere_client.embed(
                texts=[text], model="embed-english-v3.0", input_type="search_document"
            )
            embedding = list(response.embeddings)[0]
            logger.debug(f"Generated embedding with {len(embedding)} dimensions")
            return embedding
        except TooManyRequestsError:
            logger.warning("Rate limit hit. Pausing for 60 seconds...")
            time.sleep(60)
            logger.info("Retrying after rate limit pause...")


def create_indexes():
    """Creates the necessary indexes in Neo4j."""
    logger.info("Creating/ensuring indexes and constraints...")
    with get_db_session() as session:
        # Entity ID constraint
        result = session.run(
            "CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (n:Entity) REQUIRE n.id IS UNIQUE"
        )
        logger.debug("Entity ID constraint created/ensured")

        # Theme name constraint
        result = session.run(
            "CREATE CONSTRAINT theme_name IF NOT EXISTS FOR (t:Theme) REQUIRE t.name IS UNIQUE"
        )
        logger.debug("Theme name constraint created/ensured")

        # Vector index
        result = session.run(
            """
            CREATE VECTOR INDEX entity_embeddings IF NOT EXISTS
            FOR (n:Entity) ON (n.embedding)
            OPTIONS {indexConfig: {
                `vector.dimensions`: 1024,
                `vector.similarity_function`: 'cosine'
            }}
        """
        )
        logger.debug("Vector index created/ensured")

    logger.info("✅ Indexes and constraints ensured.")


def get_processed_node_ids():
    """Fetches the IDs of all nodes that already have an embedding."""
    logger.info("Checking for already processed nodes...")
    with get_db_session() as session:
        result = session.run(
            "MATCH (n:Entity) WHERE n.embedding IS NOT NULL RETURN n.id AS id"
        )
        processed_ids = {record["id"] for record in result}
        logger.info(f"Found {len(processed_ids)} nodes already processed")
        if processed_ids:
            logger.debug(f"Sample processed IDs: {list(processed_ids)[:5]}")
    return processed_ids


def test_sample_import():
    """
    Test import with just a few nodes to debug the process
    """
    logger.info("🔍 Starting debug import process...")

    # Test database connection
    logger.info("Testing database connection...")
    with get_db_session() as session:
        test_result = session.run("RETURN 1 as test").single()["test"]
        logger.info(f"✅ Database connection successful (test: {test_result})")

        # Check current database state
        node_count = session.run("MATCH (n) RETURN count(n) as count").single()["count"]
        entity_count = session.run(
            "MATCH (n:Entity) RETURN count(n) as count"
        ).single()["count"]
        logger.info(
            f"Current database state: {node_count} total nodes, {entity_count} entities"
        )

    create_indexes()
    processed_ids = get_processed_node_ids()

    # Process only first batch file with limited nodes
    batch_file = os.path.join(JSON_INPUT_PATH, "batch_1.json")
    if not os.path.exists(batch_file):
        logger.error(f"❌ Batch file not found: {batch_file}")
        return

    logger.info(f"Processing debug batch: {batch_file}")

    with open(batch_file, "r") as f:
        batch_data = json.load(f)

    nodes_processed = 0
    nodes_skipped = 0

    with get_db_session() as session:
        for chunk_idx, chunk_data in enumerate(batch_data[:1]):  # Only first chunk
            logger.info(f"Processing chunk {chunk_idx + 1}")

            for node_type, nodes in chunk_data.items():
                if isinstance(nodes, list):
                    logger.info(f"Processing {len(nodes)} {node_type} nodes")

                    for node_idx, node in enumerate(nodes[:3]):  # Only first 3 nodes
                        entity_id = node.get("name")
                        description = node.get("description") or node.get("content", "")
                        theme_name = node.get("theme")

                        logger.debug(f"Processing node {node_idx + 1}: {entity_id}")

                        if not all([entity_id, description, theme_name]):
                            logger.warning(
                                f"Skipping node due to missing data: {entity_id}"
                            )
                            continue

                        if entity_id in processed_ids:
                            logger.info(f"Skipping already processed node: {entity_id}")
                            nodes_skipped += 1
                            continue

                        # Create theme
                        logger.debug(f"Creating/ensuring theme: {theme_name}")
                        session.run(
                            "MERGE (t:Theme {name: $theme_name})",
                            theme_name=theme_name,
                        )

                        # Generate embedding
                        logger.debug(f"Generating embedding for: {entity_id}")
                        embedding = generate_embedding(description)

                        # Create entity with labels
                        entity_label = node_type.rstrip("s").capitalize()
                        logger.debug(
                            f"Creating entity with labels: Entity, {entity_label}"
                        )

                        entity_query = (
                            """
                        MERGE (e:Entity {id: $id})
                        SET e:%s, e += $props, e.embedding = $embedding
                        """
                            % entity_label
                        )

                        props_to_set = node.copy()
                        props_to_set.pop("name", None)

                        logger.debug(f"Executing entity query: {entity_query}")
                        logger.debug(f"Props to set: {list(props_to_set.keys())}")

                        session.run(
                            entity_query,
                            id=entity_id,
                            props=props_to_set,
                            embedding=embedding,
                        )

                        # Create relationship
                        logger.debug(
                            f"Creating relationship: {entity_id} -> {theme_name}"
                        )
                        rel_query = """
                        MATCH (e:Entity {id: $entity_id})
                        MATCH (t:Theme {name: $theme_name})
                        MERGE (e)-[:BELONGS_TO]->(t)
                        """
                        session.run(
                            rel_query,
                            entity_id=entity_id,
                            theme_name=theme_name,
                        )

                        nodes_processed += 1
                        logger.info(
                            f"✅ Successfully imported '{entity_id}' as {entity_label}"
                        )

                        # Verify the node was created correctly
                        verify_result = session.run(
                            "MATCH (n:Entity {id: $id}) RETURN labels(n) as labels, n.embedding IS NOT NULL as has_embedding",
                            id=entity_id,
                        ).single()

                        if verify_result:
                            logger.debug(
                                f"Verification - Labels: {verify_result['labels']}, Has embedding: {verify_result['has_embedding']}"
                            )
                        else:
                            logger.error(
                                f"❌ Node verification failed for: {entity_id}"
                            )

    logger.info(
        f"🏁 Debug import completed: {nodes_processed} processed, {nodes_skipped} skipped"
    )


if __name__ == "__main__":
    test_sample_import()
