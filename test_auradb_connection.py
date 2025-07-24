#!/usr/bin/env python3
"""
Test script to debug AuraDB connection and data synchronization issues.
"""
import os
import sys
from dotenv import load_dotenv
from neo4j import GraphDatabase
import logging

# Load environment variables
load_dotenv(override=True)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_connection(uri, username, password, name):
    """Test connection to a Neo4j database"""
    try:
        logger.info(f"Testing connection to {name}: {uri}")
        driver = GraphDatabase.driver(uri, auth=(username, password))
        
        with driver.session() as session:
            # Test basic connectivity
            result = session.run("RETURN 1 as test")
            test_value = result.single()["test"]
            logger.info(f"✅ {name} connection successful (test value: {test_value})")
            
            # Count nodes and relationships
            node_count = session.run("MATCH (n) RETURN count(n) as count").single()["count"]
            rel_count = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()["count"]
            
            # Count entities with embeddings
            entity_count = session.run("MATCH (n:Entity) RETURN count(n) as count").single()["count"]
            embedded_count = session.run("MATCH (n:Entity) WHERE n.embedding IS NOT NULL RETURN count(n) as count").single()["count"]
            
            # Count themes
            theme_count = session.run("MATCH (n:Theme) RETURN count(n) as count").single()["count"]
            
            logger.info(f"📊 {name} Statistics:")
            logger.info(f"  - Total nodes: {node_count}")
            logger.info(f"  - Total relationships: {rel_count}")
            logger.info(f"  - Entity nodes: {entity_count}")
            logger.info(f"  - Entities with embeddings: {embedded_count}")
            logger.info(f"  - Theme nodes: {theme_count}")
            
            # Get sample entity IDs
            sample_entities = session.run("MATCH (n:Entity) RETURN n.id as id LIMIT 5").values()
            logger.info(f"  - Sample entity IDs: {[e[0] for e in sample_entities]}")
            
            return {
                'success': True,
                'node_count': node_count,
                'rel_count': rel_count,
                'entity_count': entity_count,
                'embedded_count': embedded_count,
                'theme_count': theme_count,
                'sample_entities': [e[0] for e in sample_entities]
            }
            
    except Exception as e:
        logger.error(f"❌ {name} connection failed: {str(e)}")
        return {'success': False, 'error': str(e)}
    finally:
        if 'driver' in locals():
            driver.close()

def main():
    """Main test function"""
    logger.info("🔍 Starting AuraDB connection and data synchronization test")
    
    # Get connection details
    local_uri = "bolt://localhost:7687"
    local_username = os.getenv("NEO4J_USERNAME", "neo4j")
    local_password = os.getenv("NEO4J_PASSWORD", "password123")  # Docker default
    
    aura_uri = os.getenv("NEO4J_URI")
    aura_username = os.getenv("NEO4J_USERNAME")
    aura_password = os.getenv("NEO4J_PASSWORD")
    
    if not all([aura_uri, aura_username, aura_password]):
        logger.error("❌ Missing AuraDB credentials in .env file")
        sys.exit(1)
    
    logger.info("🏠 Testing LOCAL Neo4j connection...")
    local_result = test_connection(local_uri, local_username, local_password, "LOCAL")
    
    logger.info("☁️  Testing AuraDB connection...")
    aura_result = test_connection(aura_uri, aura_username, aura_password, "AuraDB")
    
    # Compare results
    if local_result['success'] and aura_result['success']:
        logger.info("📊 COMPARISON RESULTS:")
        logger.info(f"Local entities with embeddings: {local_result['embedded_count']}")
        logger.info(f"AuraDB entities with embeddings: {aura_result['embedded_count']}")
        
        if local_result['embedded_count'] > aura_result['embedded_count']:
            logger.warning(f"⚠️  Local database has {local_result['embedded_count'] - aura_result['embedded_count']} more entities with embeddings than AuraDB")
            logger.info("This suggests the import process is not working correctly")
        elif local_result['embedded_count'] == aura_result['embedded_count']:
            logger.info("✅ Both databases have the same number of entities with embeddings")
        else:
            logger.warning(f"⚠️  AuraDB has more entities than local database")
            
        # Check for data overlap
        local_sample = set(local_result['sample_entities'])
        aura_sample = set(aura_result['sample_entities'])
        overlap = local_sample.intersection(aura_sample)
        logger.info(f"Sample entity overlap: {len(overlap)}/{len(local_sample)} entities")
    
    logger.info("🏁 Test completed")

if __name__ == "__main__":
    main()