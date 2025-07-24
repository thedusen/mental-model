#!/usr/bin/env python3
"""
sync_to_auradb.py - Main orchestrator for syncing local database to AuraDB
Coordinates all sync components for complete database synchronization
"""
import os
import sys
import json
import argparse
from datetime import datetime
from dotenv import load_dotenv
import logging

# Import our sync components
from local_db_exporter import LocalDBExporter
from auradb_analyzer import AuraDBAnalyzer
from sync_engine import SyncEngine
from embedding_manager import EmbeddingManager
from sync_validator import SyncValidator
from config import cohere_client

load_dotenv(override=True)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SyncOrchestrator:
    def __init__(self, dry_run=False, verbose=False):
        self.dry_run = dry_run
        self.verbose = verbose
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Initialize components
        self.local_exporter = LocalDBExporter()
        self.auradb_analyzer = AuraDBAnalyzer()
        self.sync_engine = SyncEngine(cohere_client)
        self.embedding_manager = EmbeddingManager()
        self.validator = SyncValidator()
        
        # Storage for sync data
        self.local_export_data = None
        self.pre_sync_aura_stats = None
        self.sync_results = None
        
        if verbose:
            logging.getLogger().setLevel(logging.DEBUG)
    
    def export_local_database(self):
        """Step 1: Export complete local database structure"""
        logger.info("🚀 STEP 1: Exporting local database...")
        
        export_file = f"../backups/sync_export_{self.timestamp}.json"
        self.local_export_data = self.local_exporter.export_complete_database(export_file)
        
        if not self.local_export_data:
            logger.error("❌ Failed to export local database")
            return False
        
        logger.info(f"✅ Local database exported: {len(self.local_export_data['nodes'])} nodes, {len(self.local_export_data['relationships'])} relationships")
        return True
    
    def analyze_auradb_current_state(self):
        """Step 2: Analyze current AuraDB state"""
        logger.info("🔍 STEP 2: Analyzing current AuraDB state...")
        
        auradb_analysis = self.auradb_analyzer.analyze_complete_database()
        if not auradb_analysis:
            logger.error("❌ Failed to analyze AuraDB")
            return False
        
        self.pre_sync_aura_stats = auradb_analysis['statistics']
        
        logger.info(f"✅ AuraDB analyzed: {self.pre_sync_aura_stats['total_nodes']} nodes, {self.pre_sync_aura_stats['total_relationships']} relationships")
        
        # Compare with local for initial assessment
        local_stats = self.local_export_data['statistics']
        node_diff = local_stats['total_nodes'] - self.pre_sync_aura_stats['total_nodes']
        rel_diff = local_stats['total_relationships'] - self.pre_sync_aura_stats['total_relationships']
        
        logger.info(f"📊 Sync needed: {node_diff} nodes, {rel_diff} relationships to sync")
        
        return True
    
    def optimize_embeddings(self):
        """Step 3: Optimize embedding generation"""
        logger.info("🧠 STEP 3: Optimizing embedding generation...")
        
        # Connect to AuraDB to get existing embeddings
        auradb_driver = None
        try:
            from neo4j import GraphDatabase
            auradb_driver = GraphDatabase.driver(
                os.getenv("NEO4J_URI"),
                auth=(os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD"))
            )
            
            # Optimize embeddings with reuse strategy
            embedding_stats = self.embedding_manager.optimize_embedding_strategy(
                self.local_export_data['nodes'],
                auradb_driver
            )
            
            logger.info(f"✅ Embedding optimization complete: {embedding_stats['embeddings_generated']} new, {embedding_stats['embeddings_reused']} reused")
            
        except Exception as e:
            logger.error(f"❌ Embedding optimization failed: {str(e)}")
            return False
        finally:
            if auradb_driver:
                auradb_driver.close()
        
        return True
    
    def perform_sync(self):
        """Step 4: Perform the actual sync"""
        if self.dry_run:
            logger.info("🧪 STEP 4: Performing DRY RUN analysis...")
            self.sync_results = self.sync_engine.perform_complete_sync(
                self.local_export_data, 
                dry_run=True
            )
        else:
            logger.info("🚀 STEP 4: Performing LIVE SYNC to AuraDB...")
            self.sync_results = self.sync_engine.perform_complete_sync(
                self.local_export_data, 
                dry_run=False
            )
        
        if not self.sync_results or not self.sync_results.get('success', False):
            logger.error("❌ Sync operation failed")
            return False
        
        if self.dry_run:
            logger.info("✅ Dry run analysis completed successfully")
        else:
            logger.info("✅ Live sync completed successfully")
        
        return True
    
    def validate_sync_results(self):
        """Step 5: Validate sync results"""
        if self.dry_run:
            logger.info("🧪 STEP 5: Skipping validation for dry run")
            return True
        
        logger.info("✅ STEP 5: Validating sync results...")
        
        # Get sample entities for validation
        sample_entities = []
        for node in self.local_export_data['nodes'][:10]:  # First 10 entities
            if 'Entity' in node['labels'] and 'id' in node['properties']:
                sample_entities.append(node['properties']['id'])
        
        # Perform complete validation
        validation_report = self.validator.perform_complete_validation(
            pre_sync_aura_stats=self.pre_sync_aura_stats,
            sample_entities=sample_entities
        )
        
        # Save validation report
        report_file = f"../backups/validation_report_{self.timestamp}.json"
        with open(report_file, 'w') as f:
            json.dump(validation_report, f, indent=2, default=str)
        
        logger.info(f"📋 Validation report saved: {report_file}")
        
        if validation_report['overall_status'] == 'SUCCESS':
            logger.info("✅ VALIDATION PASSED: Sync completed successfully!")
            return True
        elif validation_report['overall_status'] == 'SUCCESS_WITH_WARNINGS':
            logger.warning("⚠️ VALIDATION PASSED WITH WARNINGS")
            return True
        else:
            logger.error("❌ VALIDATION FAILED: Sync incomplete")
            return False
    
    def generate_sync_report(self):
        """Generate comprehensive sync report"""
        logger.info("📋 Generating sync report...")
        
        report = {
            'sync_metadata': {
                'timestamp': self.timestamp,
                'dry_run': self.dry_run,
                'sync_completed': datetime.now().isoformat()
            },
            'local_export_summary': {
                'total_nodes': len(self.local_export_data['nodes']) if self.local_export_data else 0,
                'total_relationships': len(self.local_export_data['relationships']) if self.local_export_data else 0,
                'statistics': self.local_export_data['statistics'] if self.local_export_data else None
            },
            'pre_sync_auradb_state': self.pre_sync_aura_stats,
            'sync_results': self.sync_results,
            'sync_status': 'SUCCESS' if self.sync_results and self.sync_results.get('success') else 'FAILED'
        }
        
        # Save report
        report_file = f"../backups/sync_report_{self.timestamp}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"📋 Sync report saved: {report_file}")
        
        # Print summary
        logger.info("📊 SYNC SUMMARY:")
        if self.dry_run:
            logger.info("   Mode: DRY RUN (no changes made)")
            if self.sync_results:
                logger.info(f"   Would create: {self.sync_results.get('entities_to_create', 0)} entities")
                logger.info(f"   Would update: {self.sync_results.get('entities_to_update', 0)} entities")
                logger.info(f"   Would create: {self.sync_results.get('relationships_to_create', 0)} relationships")
        else:
            logger.info("   Mode: LIVE SYNC")
            if self.sync_results:
                logger.info(f"   Nodes created: {self.sync_results.get('nodes_created', 0)}")
                logger.info(f"   Nodes updated: {self.sync_results.get('nodes_updated', 0)}")
                logger.info(f"   Relationships created: {self.sync_results.get('relationships_created', 0)}")
        
        return report
    
    def run_complete_sync(self):
        """Run the complete sync process"""
        logger.info("🚀 Starting complete database sync process...")
        logger.info(f"   Mode: {'DRY RUN' if self.dry_run else 'LIVE SYNC'}")
        logger.info(f"   Timestamp: {self.timestamp}")
        
        try:
            # Step 1: Export local database
            if not self.export_local_database():
                return False
            
            # Step 2: Analyze AuraDB
            if not self.analyze_auradb_current_state():
                return False
            
            # Step 3: Optimize embeddings
            if not self.optimize_embeddings():
                return False
            
            # Step 4: Perform sync
            if not self.perform_sync():
                return False
            
            # Step 5: Validate results (skip for dry run)
            if not self.validate_sync_results():
                return False
            
            # Generate final report
            self.generate_sync_report()
            
            logger.info("🎉 SYNC PROCESS COMPLETED SUCCESSFULLY!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Sync process failed: {str(e)}")
            return False

def main():
    """Main function with command line argument support"""
    parser = argparse.ArgumentParser(description='Sync local Neo4j database to AuraDB')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Perform dry run without making changes')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    parser.add_argument('--export-only', action='store_true',
                       help='Only export local database, do not sync')
    
    args = parser.parse_args()
    
    # Create orchestrator
    orchestrator = SyncOrchestrator(dry_run=args.dry_run, verbose=args.verbose)
    
    if args.export_only:
        logger.info("📤 Export-only mode")
        success = orchestrator.export_local_database()
    else:
        # Run complete sync
        success = orchestrator.run_complete_sync()
    
    if success:
        print(f"✅ Operation completed successfully!")
        sys.exit(0)
    else:
        print(f"❌ Operation failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()