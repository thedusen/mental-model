#!/usr/bin/env python3
"""
AuraDBAnalyzer - Analyzes current state of AuraDB production database
Captures existing nodes, labels, properties, and relationships for comparison with local
"""
import os
import json
from datetime import datetime
from dotenv import load_dotenv
from neo4j import GraphDatabase
import logging

load_dotenv(override=True)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AuraDBAnalyzer:
    def __init__(self):
        self.aura_uri = os.getenv("NEO4J_URI")
        self.aura_username = os.getenv("NEO4J_USERNAME")
        self.aura_password = os.getenv("NEO4J_PASSWORD")
        self.driver = None
        
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
                logger.info("✅ Connected to AuraDB database")
                return True
        except Exception as e:
            logger.error(f"❌ Failed to connect to AuraDB: {str(e)}")
            return False
    
    def analyze_nodes(self):
        """Analyze all nodes in AuraDB with their labels and properties"""
        logger.info("📊 Analyzing AuraDB nodes...")
        
        with self.driver.session() as session:
            # Get all nodes with their properties
            result = session.run("""
                MATCH (n)
                RETURN elementId(n) as element_id,
                       labels(n) as labels, 
                       properties(n) as props
                ORDER BY elementId(n)
            """)
            
            nodes = []
            node_by_entity_id = {}  # Map entity.id to node data for easy lookup
            
            for record in result:
                node_data = {
                    'element_id': record['element_id'],
                    'labels': record['labels'],
                    'properties': dict(record['props'])
                }
                nodes.append(node_data)
                
                # If this is an Entity with an id property, add to lookup map
                if 'Entity' in record['labels'] and 'id' in record['props']:
                    entity_id = record['props']['id']
                    node_by_entity_id[entity_id] = node_data
            
            logger.info(f"✅ Analyzed {len(nodes)} nodes in AuraDB")
            return {
                'nodes': nodes,
                'entity_lookup': node_by_entity_id
            }
    
    def analyze_relationships(self):
        """Analyze all relationships in AuraDB"""
        logger.info("🔗 Analyzing AuraDB relationships...")
        
        with self.driver.session() as session:
            # Get all relationships
            result = session.run("""
                MATCH (a)-[r]->(b)
                RETURN elementId(a) as from_element_id,
                       elementId(b) as to_element_id,
                       elementId(r) as rel_element_id,
                       type(r) as rel_type,
                       properties(r) as rel_props,
                       a.id as from_entity_id,
                       b.id as to_entity_id
                ORDER BY elementId(r)
            """)
            
            relationships = []
            rel_by_entities = {}  # Map (from_entity_id, to_entity_id, rel_type) to relationship
            
            for record in result:
                rel_data = {
                    'rel_element_id': record['rel_element_id'],
                    'from_element_id': record['from_element_id'],
                    'to_element_id': record['to_element_id'],
                    'rel_type': record['rel_type'],
                    'properties': dict(record['rel_props']),
                    'from_entity_id': record['from_entity_id'],
                    'to_entity_id': record['to_entity_id']
                }
                relationships.append(rel_data)
                
                # Create lookup key for relationship existence checking
                if record['from_entity_id'] and record['to_entity_id']:
                    key = (record['from_entity_id'], record['to_entity_id'], record['rel_type'])
                    rel_by_entities[key] = rel_data
            
            logger.info(f"✅ Analyzed {len(relationships)} relationships in AuraDB")
            return {
                'relationships': relationships,
                'entity_relationship_lookup': rel_by_entities
            }
    
    def get_database_stats(self):
        """Get comprehensive AuraDB statistics"""
        logger.info("📈 Collecting AuraDB statistics...")
        
        with self.driver.session() as session:
            # Basic counts
            node_count = session.run("MATCH (n) RETURN count(n) as count").single()["count"]
            rel_count = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()["count"]
            
            # Label counts
            label_counts = {}
            labels_result = session.run("CALL db.labels()").values()
            for label_record in labels_result:
                label = label_record[0]
                count = session.run(f"MATCH (n:`{label}`) RETURN count(n) as count").single()["count"]
                label_counts[label] = count
            
            # Relationship type counts
            rel_type_counts = {}
            rel_types_result = session.run("CALL db.relationshipTypes()").values()
            for rel_type_record in rel_types_result:
                rel_type = rel_type_record[0]
                count = session.run(f"MATCH ()-[r:`{rel_type}`]->() RETURN count(r) as count").single()["count"]
                rel_type_counts[rel_type] = count
            
            stats = {
                'total_nodes': node_count,
                'total_relationships': rel_count,
                'label_counts': label_counts,
                'relationship_type_counts': rel_type_counts,
                'analysis_timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"✅ AuraDB stats: {node_count} nodes, {rel_count} relationships")
            return stats
    
    def analyze_complete_database(self, output_file=None):
        """Analyze complete AuraDB structure"""
        if not self.connect():
            return None
        
        try:
            logger.info("🚀 Starting complete AuraDB analysis...")
            
            # Analyze all components
            node_analysis = self.analyze_nodes()
            rel_analysis = self.analyze_relationships()
            stats = self.get_database_stats()
            
            # Create complete analysis structure
            analysis_data = {
                'metadata': {
                    'analysis_timestamp': datetime.now().isoformat(),
                    'source_database': 'auradb',
                    'analyzer_version': '1.0'
                },
                'statistics': stats,
                'nodes': node_analysis['nodes'],
                'relationships': rel_analysis['relationships'],
                'lookups': {
                    'entity_by_id': node_analysis['entity_lookup'],
                    'relationship_by_entities': rel_analysis['entity_relationship_lookup']
                }
            }
            
            # Save to file if requested
            if output_file:
                os.makedirs(os.path.dirname(output_file), exist_ok=True)
                with open(output_file, 'w') as f:
                    json.dump(analysis_data, f, indent=2, default=str)
                logger.info(f"✅ AuraDB analysis saved to: {output_file}")
            
            logger.info(f"📊 Analysis summary: {len(node_analysis['nodes'])} nodes, {len(rel_analysis['relationships'])} relationships")
            
            return analysis_data
            
        except Exception as e:
            logger.error(f"❌ Analysis failed: {str(e)}")
            return None
        finally:
            if self.driver:
                self.driver.close()
    
    def compare_with_local_export(self, local_export_data):
        """Compare AuraDB state with local export data"""
        logger.info("🔍 Comparing AuraDB with local database...")
        
        auradb_data = self.analyze_complete_database()
        if not auradb_data:
            return None
        
        # Compare statistics
        local_stats = local_export_data['statistics']
        auradb_stats = auradb_data['statistics']
        
        comparison = {
            'timestamp': datetime.now().isoformat(),
            'statistics_comparison': {
                'local': local_stats,
                'auradb': auradb_stats,
                'differences': {
                    'node_count_diff': local_stats['total_nodes'] - auradb_stats['total_nodes'],
                    'rel_count_diff': local_stats['total_relationships'] - auradb_stats['total_relationships']
                }
            },
            'missing_in_auradb': {
                'nodes': [],
                'relationships': []
            },
            'extra_in_auradb': {
                'nodes': [],
                'relationships': []
            }
        }
        
        # Find missing entities in AuraDB
        local_entity_ids = set()
        for node in local_export_data['nodes']:
            if 'Entity' in node['labels'] and 'id' in node['properties']:
                local_entity_ids.add(node['properties']['id'])
        
        auradb_entity_ids = set(auradb_data['lookups']['entity_by_id'].keys())
        
        missing_entities = local_entity_ids - auradb_entity_ids
        extra_entities = auradb_entity_ids - local_entity_ids
        
        comparison['missing_in_auradb']['entity_ids'] = list(missing_entities)
        comparison['extra_in_auradb']['entity_ids'] = list(extra_entities)
        
        logger.info(f"📊 Comparison complete:")
        logger.info(f"   - Missing entities in AuraDB: {len(missing_entities)}")
        logger.info(f"   - Extra entities in AuraDB: {len(extra_entities)}")
        logger.info(f"   - Node count difference: {comparison['statistics_comparison']['differences']['node_count_diff']}")
        logger.info(f"   - Relationship count difference: {comparison['statistics_comparison']['differences']['rel_count_diff']}")
        
        return comparison

def main():
    """Main function for standalone execution"""
    analyzer = AuraDBAnalyzer()
    result = analyzer.analyze_complete_database()
    
    if result:
        print("✅ AuraDB analysis completed successfully!")
        print(f"   - {result['statistics']['total_nodes']} nodes analyzed")
        print(f"   - {result['statistics']['total_relationships']} relationships analyzed")
        print(f"   - Label counts: {result['statistics']['label_counts']}")
        print(f"   - Relationship type counts: {result['statistics']['relationship_type_counts']}")
    else:
        print("❌ AuraDB analysis failed!")

if __name__ == "__main__":
    main()