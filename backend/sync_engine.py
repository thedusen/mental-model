#!/usr/bin/env python3
"""
SyncEngine - Performs intelligent differential sync from local database to AuraDB
Handles nodes, labels, properties, and relationships with minimal disruption
"""
import os
import json
from datetime import datetime
from dotenv import load_dotenv
from neo4j import GraphDatabase
import logging
from cohere.errors import TooManyRequestsError
import time

load_dotenv(override=True)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SyncEngine:
    def __init__(self, cohere_client=None):
        self.aura_uri = os.getenv("NEO4J_URI")
        self.aura_username = os.getenv("NEO4J_USERNAME")
        self.aura_password = os.getenv("NEO4J_PASSWORD")
        self.driver = None
        self.cohere_client = cohere_client
        
        if not all([self.aura_uri, self.aura_username, self.aura_password]):
            raise ValueError("Missing AuraDB credentials in environment variables")
    
    def connect(self):
        """Connect to AuraDB database"""
        try:
            self.driver = GraphDatabase.driver(
                self.aura_uri, 
                auth=(self.aura_username, self.aura_password)
            )
            # Test connection
            with self.driver.session() as session:
                result = session.run("RETURN 1 as test").single()
                logger.info("✅ Connected to AuraDB for sync")
                return True
        except Exception as e:
            logger.error(f"❌ Failed to connect to AuraDB: {str(e)}")
            return False
    
    def generate_embedding(self, text):
        """Generate embedding with rate limiting"""
        if not self.cohere_client:
            logger.warning("⚠️ No Cohere client available - skipping embedding generation")
            return None
            
        while True:
            try:
                response = self.cohere_client.embed(
                    texts=[text], model="embed-english-v3.0", input_type="search_document"
                )
                return list(response.embeddings)[0]
            except TooManyRequestsError:
                logger.warning("⏱️ Rate limit hit. Pausing for 60 seconds...")
                time.sleep(60)
                logger.info("Retrying embedding generation...")
            except Exception as e:
                logger.error(f"❌ Embedding generation failed: {str(e)}")
                return None
    
    def ensure_constraints_and_indexes(self):
        """Ensure necessary constraints and indexes exist in AuraDB"""
        logger.info("🔧 Ensuring constraints and indexes in AuraDB...")
        
        with self.driver.session() as session:
            # Entity ID constraint
            session.run(
                "CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (n:Entity) REQUIRE n.id IS UNIQUE"
            )
            
            # Theme name constraint  
            session.run(
                "CREATE CONSTRAINT theme_name IF NOT EXISTS FOR (t:Theme) REQUIRE t.name IS UNIQUE"
            )
            
            # Vector index
            session.run(
                """
                CREATE VECTOR INDEX entity_embeddings IF NOT EXISTS
                FOR (n:Entity) ON (n.embedding)
                OPTIONS {indexConfig: {
                    `vector.dimensions`: 1024,
                    `vector.similarity_function`: 'cosine'
                }}
            """
            )
            
        logger.info("✅ Constraints and indexes ensured")
    
    def get_auradb_entity_ids(self):
        """Get all entity IDs currently in AuraDB"""
        with self.driver.session() as session:
            result = session.run("MATCH (n:Entity) RETURN n.id as id")
            return {record["id"] for record in result}
    
    def get_auradb_relationships(self):
        """Get all relationships currently in AuraDB"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (a:Entity)-[r]->(b:Entity)
                RETURN a.id as from_id, b.id as to_id, type(r) as rel_type
            """)
            return {(record["from_id"], record["to_id"], record["rel_type"]) for record in result}
    
    def sync_nodes_batch(self, local_nodes, batch_size=50):
        """Sync nodes in batches to AuraDB"""
        logger.info(f"📦 Syncing {len(local_nodes)} nodes in batches of {batch_size}...")
        
        existing_entity_ids = self.get_auradb_entity_ids()
        nodes_created = 0
        nodes_updated = 0
        
        with self.driver.session() as session:
            for i in range(0, len(local_nodes), batch_size):
                batch = local_nodes[i:i + batch_size]
                logger.info(f"  Processing batch {i//batch_size + 1}/{(len(local_nodes) + batch_size - 1)//batch_size}")
                
                for node in batch:
                    if 'Entity' not in node['labels']:
                        continue  # Skip non-Entity nodes for now
                    
                    entity_id = node['properties'].get('id')
                    if not entity_id:
                        logger.warning(f"⚠️ Node without id property: {node['labels']}")
                        continue
                    
                    # Check if we need to generate embedding
                    description = node['properties'].get('description') or node['properties'].get('content', '')
                    needs_embedding = 'embedding' not in node['properties'] and description
                    
                    if needs_embedding and self.cohere_client:
                        logger.debug(f"Generating embedding for: {entity_id}")
                        embedding = self.generate_embedding(description)
                        if embedding:
                            node['properties']['embedding'] = embedding
                    
                    # Prepare all labels for the node
                    labels_str = ':'.join(node['labels'])
                    
                    # Create/Update node with all labels and properties
                    query = f"""
                    MERGE (e:Entity {{id: $id}})
                    SET e:{labels_str}
                    SET e += $props
                    """
                    
                    try:
                        session.run(query, id=entity_id, props=node['properties'])
                        
                        if entity_id in existing_entity_ids:
                            nodes_updated += 1
                        else:
                            nodes_created += 1
                            
                    except Exception as e:
                        logger.error(f"❌ Failed to sync node {entity_id}: {str(e)}")
        
        logger.info(f"✅ Nodes sync complete: {nodes_created} created, {nodes_updated} updated")
        return nodes_created, nodes_updated
    
    def sync_theme_nodes(self, local_nodes):
        """Sync Theme nodes to AuraDB"""
        logger.info("🏷️ Syncing theme nodes...")
        
        theme_nodes = [node for node in local_nodes if 'Theme' in node['labels']]
        
        with self.driver.session() as session:
            for theme_node in theme_nodes:
                theme_name = theme_node['properties'].get('name')
                if theme_name:
                    session.run(
                        "MERGE (t:Theme {name: $name}) SET t += $props",
                        name=theme_name,
                        props=theme_node['properties']
                    )
        
        logger.info(f"✅ Synced {len(theme_nodes)} theme nodes")
    
    def sync_relationships_batch(self, local_relationships, batch_size=100):
        """Sync relationships in batches to AuraDB"""
        logger.info(f"🔗 Syncing {len(local_relationships)} relationships in batches of {batch_size}...")
        
        existing_relationships = self.get_auradb_relationships()
        relationships_created = 0
        
        # Build mapping from neo_id to entity_id for local nodes
        local_entity_map = {}
        for rel in local_relationships:
            # We'll need to get this mapping from the exported data
            pass
        
        with self.driver.session() as session:
            for i in range(0, len(local_relationships), batch_size):
                batch = local_relationships[i:i + batch_size]
                logger.info(f"  Processing relationship batch {i//batch_size + 1}/{(len(local_relationships) + batch_size - 1)//batch_size}")
                
                for rel in batch:
                    # Skip if this relationship already exists
                    # Note: We'll need to map neo_ids to entity_ids here
                    # For now, we'll create a basic relationship sync
                    
                    rel_type = rel['rel_type']
                    rel_props = rel.get('properties', {})
                    
                    # Create the relationship query
                    query = f"""
                    MATCH (a:Entity), (b:Entity)
                    WHERE elementId(a) = $from_id AND elementId(b) = $to_id
                    MERGE (a)-[r:{rel_type}]->(b)
                    SET r += $props
                    """
                    
                    try:
                        result = session.run(
                            query, 
                            from_id=rel['from_neo_id'], 
                            to_id=rel['to_neo_id'],
                            props=rel_props
                        )
                        relationships_created += 1
                    except Exception as e:
                        logger.debug(f"Relationship sync issue (may be normal): {str(e)}")
        
        logger.info(f"✅ Relationships sync complete: {relationships_created} processed")
        return relationships_created
    
    def sync_entity_relationships_by_id(self, local_export_data):
        """Sync relationships using entity IDs instead of neo4j internal IDs"""
        logger.info("🔗 Syncing entity-to-entity relationships by ID...")
        
        # Build mapping from neo_id to entity_id
        neo_id_to_entity_id = {}
        for node in local_export_data['nodes']:
            if 'Entity' in node['labels'] and 'id' in node['properties']:
                neo_id_to_entity_id[node['neo_id']] = node['properties']['id']
        
        relationships_created = 0
        with self.driver.session() as session:
            for rel in local_export_data['relationships']:
                from_entity_id = neo_id_to_entity_id.get(rel['from_neo_id'])
                to_entity_id = neo_id_to_entity_id.get(rel['to_neo_id'])
                
                if not from_entity_id or not to_entity_id:
                    continue  # Skip relationships to non-Entity nodes
                
                rel_type = rel['rel_type']
                rel_props = rel.get('properties', {})
                
                # Create relationship between entities by their ID property
                query = f"""
                MATCH (a:Entity {{id: $from_id}})
                MATCH (b:Entity {{id: $to_id}})
                MERGE (a)-[r:{rel_type}]->(b)
                SET r += $props
                """
                
                try:
                    session.run(
                        query,
                        from_id=from_entity_id,
                        to_id=to_entity_id,
                        props=rel_props
                    )
                    relationships_created += 1
                except Exception as e:
                    logger.debug(f"Relationship creation issue: {str(e)}")
        
        logger.info(f"✅ Entity relationships sync complete: {relationships_created} created")
        return relationships_created
    
    def perform_complete_sync(self, local_export_data, dry_run=False):
        """Perform complete sync from local export data to AuraDB"""
        if not self.connect():
            return False
        
        try:
            if dry_run:
                logger.info("🧪 PERFORMING DRY RUN - NO CHANGES WILL BE MADE")
                return self.analyze_sync_changes(local_export_data)
            
            logger.info("🚀 Starting complete database sync to AuraDB...")
            
            # Ensure schema
            self.ensure_constraints_and_indexes()
            
            # Sync theme nodes first
            self.sync_theme_nodes(local_export_data['nodes'])
            
            # Sync entity nodes
            nodes_created, nodes_updated = self.sync_nodes_batch(local_export_data['nodes'])
            
            # Sync relationships
            relationships_created = self.sync_entity_relationships_by_id(local_export_data)
            
            logger.info("✅ Complete sync finished!")
            logger.info(f"   📊 Summary: {nodes_created} nodes created, {nodes_updated} nodes updated")
            logger.info(f"   🔗 {relationships_created} relationships created")
            
            return {
                'success': True,
                'nodes_created': nodes_created,
                'nodes_updated': nodes_updated,
                'relationships_created': relationships_created
            }
            
        except Exception as e:
            logger.error(f"❌ Sync failed: {str(e)}")
            return {'success': False, 'error': str(e)}
        finally:
            if self.driver:
                self.driver.close()
    
    def analyze_sync_changes(self, local_export_data):
        """Analyze what changes would be made during sync (dry run)"""
        logger.info("🔍 Analyzing sync changes (dry run mode)...")
        
        existing_entity_ids = self.get_auradb_entity_ids()
        existing_relationships = self.get_auradb_relationships()
        
        # Count entities that would be created vs updated
        local_entity_ids = set()
        for node in local_export_data['nodes']:
            if 'Entity' in node['labels'] and 'id' in node['properties']:
                local_entity_ids.add(node['properties']['id'])
        
        entities_to_create = local_entity_ids - existing_entity_ids
        entities_to_update = local_entity_ids & existing_entity_ids
        
        # Count relationships that would be created
        neo_id_to_entity_id = {}
        for node in local_export_data['nodes']:
            if 'Entity' in node['labels'] and 'id' in node['properties']:
                neo_id_to_entity_id[node['neo_id']] = node['properties']['id']
        
        local_relationships = set()
        for rel in local_export_data['relationships']:
            from_entity_id = neo_id_to_entity_id.get(rel['from_neo_id'])
            to_entity_id = neo_id_to_entity_id.get(rel['to_neo_id'])
            
            if from_entity_id and to_entity_id:
                local_relationships.add((from_entity_id, to_entity_id, rel['rel_type']))
        
        relationships_to_create = local_relationships - existing_relationships
        
        analysis = {
            'entities_to_create': len(entities_to_create),
            'entities_to_update': len(entities_to_update),
            'relationships_to_create': len(relationships_to_create),
            'sample_new_entities': list(entities_to_create)[:5],
            'sample_new_relationships': list(relationships_to_create)[:5]
        }
        
        logger.info(f"📊 Dry run analysis:")
        logger.info(f"   - Entities to create: {analysis['entities_to_create']}")
        logger.info(f"   - Entities to update: {analysis['entities_to_update']}")  
        logger.info(f"   - Relationships to create: {analysis['relationships_to_create']}")
        
        return analysis

def main():
    """Main function for standalone testing"""
    sync_engine = SyncEngine()
    print("SyncEngine initialized successfully!")

if __name__ == "__main__":
    main()