#!/usr/bin/env python3
"""
LocalDBExporter - Exports complete structure of local Neo4j database
Captures all nodes, labels, properties, and relationships for sync to AuraDB
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

class LocalDBExporter:
    def __init__(self):
        self.local_uri = "bolt://localhost:7687"
        self.local_username = os.getenv("NEO4J_USERNAME", "neo4j")
        self.local_password = os.getenv("NEO4J_PASSWORD", "password123")
        self.driver = None
        
    def connect(self):
        """Connect to local Neo4j database"""
        try:
            self.driver = GraphDatabase.driver(
                self.local_uri, 
                auth=(self.local_username, self.local_password)
            )
            # Test connection
            with self.driver.session() as session:
                result = session.run("RETURN 1 as test").single()
                logger.info("✅ Connected to local Neo4j database")
                return True
        except Exception as e:
            logger.error(f"❌ Failed to connect to local database: {str(e)}")
            return False
    
    def export_nodes(self):
        """Export all nodes with their labels and properties"""
        logger.info("📊 Exporting all nodes...")
        
        with self.driver.session() as session:
            # Get all nodes with their Neo4j internal IDs, labels, and properties
            result = session.run("""
                MATCH (n)
                RETURN id(n) as neo_id, 
                       labels(n) as labels, 
                       properties(n) as props
                ORDER BY id(n)
            """)
            
            nodes = []
            for record in result:
                node_data = {
                    'neo_id': record['neo_id'],
                    'labels': record['labels'],
                    'properties': dict(record['props'])  # Convert to regular dict
                }
                nodes.append(node_data)
            
            logger.info(f"✅ Exported {len(nodes)} nodes")
            return nodes
    
    def export_relationships(self):
        """Export all relationships with their types and properties"""
        logger.info("🔗 Exporting all relationships...")
        
        with self.driver.session() as session:
            # Get all relationships with source/target neo IDs
            result = session.run("""
                MATCH (a)-[r]->(b)
                RETURN id(a) as from_neo_id,
                       id(b) as to_neo_id,
                       id(r) as rel_neo_id,
                       type(r) as rel_type,
                       properties(r) as rel_props
                ORDER BY id(r)
            """)
            
            relationships = []
            for record in result:
                rel_data = {
                    'rel_neo_id': record['rel_neo_id'],
                    'from_neo_id': record['from_neo_id'],
                    'to_neo_id': record['to_neo_id'],
                    'rel_type': record['rel_type'],
                    'properties': dict(record['rel_props'])  # Convert to regular dict
                }
                relationships.append(rel_data)
            
            logger.info(f"✅ Exported {len(relationships)} relationships")
            return relationships
    
    def export_constraints_and_indexes(self):
        """Export database constraints and indexes"""
        logger.info("🔧 Exporting constraints and indexes...")
        
        with self.driver.session() as session:
            # Get constraints
            try:
                constraints_result = session.run("SHOW CONSTRAINTS")
                constraints = [dict(record) for record in constraints_result]
            except:
                # Fallback for older Neo4j versions
                constraints = []
                logger.warning("Could not export constraints (older Neo4j version)")
            
            # Get indexes
            try:
                indexes_result = session.run("SHOW INDEXES")
                indexes = [dict(record) for record in indexes_result]
            except:
                # Fallback for older Neo4j versions
                indexes = []
                logger.warning("Could not export indexes (older Neo4j version)")
            
            logger.info(f"✅ Exported {len(constraints)} constraints and {len(indexes)} indexes")
            return {
                'constraints': constraints,
                'indexes': indexes
            }
    
    def get_database_stats(self):
        """Get comprehensive database statistics"""
        logger.info("📈 Collecting database statistics...")
        
        with self.driver.session() as session:
            # Basic counts
            node_count = session.run("MATCH (n) RETURN count(n) as count").single()["count"]
            rel_count = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()["count"]
            
            # Label counts
            label_counts = {}
            try:
                result = session.run("""
                    CALL db.labels() YIELD label
                    CALL apoc.cypher.run('MATCH (n:`' + label + '`) RETURN count(n) as count', {}) 
                    YIELD value
                    RETURN label, value.count as count
                """)
                for record in result:
                    label_counts[record['label']] = record['count']
            except:
                # Fallback without APOC
                labels_result = session.run("CALL db.labels()").values()
                for label_record in labels_result:
                    label = label_record[0]
                    count = session.run(f"MATCH (n:`{label}`) RETURN count(n) as count").single()["count"]
                    label_counts[label] = count
            
            # Relationship type counts
            rel_type_counts = {}
            try:
                result = session.run("""
                    CALL db.relationshipTypes() YIELD relationshipType
                    CALL apoc.cypher.run('MATCH ()-[r:`' + relationshipType + '`]->() RETURN count(r) as count', {}) 
                    YIELD value
                    RETURN relationshipType, value.count as count
                """)
                for record in result:
                    rel_type_counts[record['relationshipType']] = record['count']
            except:
                # Fallback without APOC
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
                'export_timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"✅ Database stats: {node_count} nodes, {rel_count} relationships")
            return stats
    
    def export_complete_database(self, output_file=None):
        """Export complete database structure to JSON file"""
        if not self.connect():
            return None
        
        try:
            logger.info("🚀 Starting complete database export...")
            
            # Export all components
            nodes = self.export_nodes()
            relationships = self.export_relationships()
            schema = self.export_constraints_and_indexes()
            stats = self.get_database_stats()
            
            # Create complete export structure
            export_data = {
                'metadata': {
                    'export_timestamp': datetime.now().isoformat(),
                    'source_database': 'local_neo4j',
                    'exporter_version': '1.0'
                },
                'statistics': stats,
                'schema': schema,
                'nodes': nodes,
                'relationships': relationships
            }
            
            # Save to file
            if output_file is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file = f"../backups/local_db_export_{timestamp}.json"
            
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            with open(output_file, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)
            
            logger.info(f"✅ Complete database export saved to: {output_file}")
            logger.info(f"📊 Export summary: {len(nodes)} nodes, {len(relationships)} relationships")
            
            return export_data
            
        except Exception as e:
            logger.error(f"❌ Export failed: {str(e)}")
            return None
        finally:
            if self.driver:
                self.driver.close()

def main():
    """Main function for standalone execution"""
    exporter = LocalDBExporter()
    result = exporter.export_complete_database()
    
    if result:
        print("✅ Export completed successfully!")
        print(f"   - {result['statistics']['total_nodes']} nodes exported")
        print(f"   - {result['statistics']['total_relationships']} relationships exported")
        print(f"   - {len(result['schema']['constraints'])} constraints exported")
        print(f"   - {len(result['schema']['indexes'])} indexes exported")
    else:
        print("❌ Export failed!")

if __name__ == "__main__":
    main()