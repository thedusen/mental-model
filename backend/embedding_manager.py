#!/usr/bin/env python3
"""
EmbeddingManager - Handles efficient embedding generation and management
Preserves existing embeddings and only generates new ones when needed
"""
import os
import hashlib
from datetime import datetime
from dotenv import load_dotenv
import cohere
from cohere.errors import TooManyRequestsError
import time
import logging

load_dotenv(override=True)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class EmbeddingManager:
    def __init__(self):
        self.cohere_client = None
        self.init_cohere_client()

    def init_cohere_client(self):
        """Initialize Cohere client"""
        api_key = os.getenv("COHERE_API_KEY")
        if api_key:
            try:
                self.cohere_client = cohere.Client(api_key=api_key)
                logger.info("✅ Cohere client initialized")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Cohere client: {str(e)}")
                self.cohere_client = None
        else:
            logger.warning("⚠️ COHERE_API_KEY not found - embedding generation disabled")

    def get_text_hash(self, text):
        """Get hash of text to detect content changes"""
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    def should_generate_embedding(self, node_data, existing_embeddings=None):
        """Determine if we need to generate a new embedding for this node"""
        entity_id = node_data["properties"].get("id")
        description = node_data["properties"].get("description") or node_data[
            "properties"
        ].get("content", "")

        # No description = no embedding needed
        if not description:
            return False, "No description available"

        # Already has embedding = preserve it
        if "embedding" in node_data["properties"]:
            return False, "Embedding already exists"

        # Check if we have existing embedding data
        if existing_embeddings and entity_id in existing_embeddings:
            existing_data = existing_embeddings[entity_id]

            # Compare content hash to see if text changed
            current_hash = self.get_text_hash(description)
            if existing_data.get("content_hash") == current_hash:
                # Content unchanged, reuse existing embedding
                node_data["properties"]["embedding"] = existing_data["embedding"]
                return False, "Reusing existing embedding (content unchanged)"

        return True, "New embedding needed"

    def generate_embedding_with_retry(self, text, max_retries=3):
        """Generate embedding with retry logic and rate limiting"""
        if not self.cohere_client:
            logger.warning("⚠️ Cohere client not available")
            return None

        for attempt in range(max_retries):
            try:
                logger.debug(
                    f"Generating embedding (attempt {attempt + 1}/{max_retries})"
                )
                response = self.cohere_client.embed(
                    texts=[text],
                    model="embed-english-v3.0",
                    input_type="search_document",
                )
                embedding = list(response.embeddings)[0]
                logger.debug(f"✅ Generated embedding with {len(embedding)} dimensions")
                return embedding

            except TooManyRequestsError:
                wait_time = 60 * (attempt + 1)  # Increasing wait time
                logger.warning(
                    f"⏱️ Rate limit hit. Waiting {wait_time} seconds (attempt {attempt + 1})..."
                )
                time.sleep(wait_time)

            except Exception as e:
                logger.error(
                    f"❌ Embedding generation failed (attempt {attempt + 1}): {str(e)}"
                )
                if attempt == max_retries - 1:
                    return None
                time.sleep(5)  # Brief pause before retry

        return None

    def process_nodes_for_embeddings(self, nodes, existing_embeddings=None):
        """Process all nodes and generate embeddings where needed"""
        logger.info(f"🧠 Processing {len(nodes)} nodes for embeddings...")

        stats = {
            "total_nodes": len(nodes),
            "embeddings_generated": 0,
            "embeddings_reused": 0,
            "embeddings_skipped": 0,
            "errors": 0,
        }

        for i, node in enumerate(nodes):
            if "Entity" not in node["labels"]:
                stats["embeddings_skipped"] += 1
                continue

            entity_id = node["properties"].get("id", f"node_{i}")

            should_generate, reason = self.should_generate_embedding(
                node, existing_embeddings
            )

            if should_generate:
                description = node["properties"].get("description") or node[
                    "properties"
                ].get("content", "")

                logger.info(f"  Generating embedding for: {entity_id}")
                embedding = self.generate_embedding_with_retry(description)

                if embedding:
                    node["properties"]["embedding"] = embedding
                    node["properties"][
                        "embedding_generated_at"
                    ] = datetime.now().isoformat()
                    node["properties"]["content_hash"] = self.get_text_hash(description)
                    stats["embeddings_generated"] += 1
                else:
                    logger.error(f"❌ Failed to generate embedding for: {entity_id}")
                    stats["errors"] += 1
            else:
                if "reusing" in reason.lower():
                    stats["embeddings_reused"] += 1
                else:
                    stats["embeddings_skipped"] += 1

                logger.debug(f"  Skipping {entity_id}: {reason}")

        logger.info(f"✅ Embedding processing complete:")
        logger.info(f"   - Generated: {stats['embeddings_generated']}")
        logger.info(f"   - Reused: {stats['embeddings_reused']}")
        logger.info(f"   - Skipped: {stats['embeddings_skipped']}")
        logger.info(f"   - Errors: {stats['errors']}")

        return stats

    def extract_existing_embeddings_from_auradb(self, auradb_driver):
        """Extract existing embeddings from AuraDB to avoid regeneration"""
        logger.info("📥 Extracting existing embeddings from AuraDB...")

        existing_embeddings = {}

        try:
            with auradb_driver.session() as session:
                result = session.run(
                    """
                    MATCH (e:Entity)
                    WHERE e.embedding IS NOT NULL
                    RETURN e.id as entity_id, 
                           e.embedding as embedding,
                           e.content_hash as content_hash,
                           e.description as description,
                           e.content as content
                """
                )

                for record in result:
                    entity_id = record["entity_id"]
                    if entity_id:
                        # Get current content to compute hash
                        description = record["description"] or record["content"] or ""
                        current_hash = (
                            self.get_text_hash(description) if description else None
                        )

                        existing_embeddings[entity_id] = {
                            "embedding": record["embedding"],
                            "content_hash": record["content_hash"] or current_hash,
                            "description": description,
                        }

                logger.info(
                    f"✅ Extracted {len(existing_embeddings)} existing embeddings from AuraDB"
                )

        except Exception as e:
            logger.error(f"❌ Failed to extract embeddings from AuraDB: {str(e)}")

        return existing_embeddings

    def optimize_embedding_strategy(self, local_nodes, auradb_driver=None):
        """Optimize embedding generation strategy by reusing existing embeddings"""
        logger.info("🎯 Optimizing embedding generation strategy...")

        existing_embeddings = {}
        if auradb_driver:
            existing_embeddings = self.extract_existing_embeddings_from_auradb(
                auradb_driver
            )

        # Process nodes with optimization
        stats = self.process_nodes_for_embeddings(local_nodes, existing_embeddings)

        return stats

    def validate_embeddings(self, nodes):
        """Validate that embeddings are properly formatted"""
        logger.info("✅ Validating embeddings...")

        validation_stats = {
            "total_entities": 0,
            "valid_embeddings": 0,
            "invalid_embeddings": 0,
            "missing_embeddings": 0,
        }

        for node in nodes:
            if "Entity" not in node["labels"]:
                continue

            validation_stats["total_entities"] += 1

            embedding = node["properties"].get("embedding")
            if not embedding:
                validation_stats["missing_embeddings"] += 1
                continue

            # Validate embedding format
            if isinstance(embedding, list) and len(embedding) == 1024:
                validation_stats["valid_embeddings"] += 1
            else:
                validation_stats["invalid_embeddings"] += 1
                logger.warning(
                    f"⚠️ Invalid embedding for {node['properties'].get('id')}"
                )

        logger.info(f"📊 Embedding validation:")
        logger.info(f"   - Valid: {validation_stats['valid_embeddings']}")
        logger.info(f"   - Invalid: {validation_stats['invalid_embeddings']}")
        logger.info(f"   - Missing: {validation_stats['missing_embeddings']}")

        return validation_stats


def main():
    """Main function for standalone testing"""
    manager = EmbeddingManager()

    # Test embedding generation
    test_text = "This is a test description for embedding generation."
    embedding = manager.generate_embedding_with_retry(test_text)

    if embedding:
        print(f"✅ Test embedding generated successfully! Dimensions: {len(embedding)}")
    else:
        print("❌ Test embedding generation failed!")


if __name__ == "__main__":
    main()
