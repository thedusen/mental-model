#!/usr/bin/env python3
"""
Debug script to understand why we're getting different counts from AuraDB
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


def debug_auradb_access():
    aura_uri = os.getenv("NEO4J_URI")
    aura_username = os.getenv("NEO4J_USERNAME")
    aura_password = os.getenv("NEO4J_PASSWORD")

    logger.info(f"🔍 Debugging AuraDB access")
    logger.info(f"URI: {aura_uri}")
    logger.info(f"Username: {aura_username}")

    try:
        driver = GraphDatabase.driver(aura_uri, auth=(aura_username, aura_password))

        with driver.session() as session:
            # Check which database we're connected to
            try:
                db_info = session.run("CALL db.info()").single()
                logger.info(f"📊 Database info: {dict(db_info)}")
            except:
                logger.info("📊 Could not get database info")

            # Try different node counting methods
            logger.info("\n🔢 DIFFERENT COUNTING METHODS:")

            # Method 1: Simple count
            result1 = session.run("MATCH (n) RETURN count(n) as count").single()
            logger.info(f"Method 1 - Simple count: {result1['count']}")

            # Method 2: Count with database specification
            try:
                result2 = session.run(
                    "MATCH (n) RETURN count(n) as count", database="neo4j"
                ).single()
                logger.info(f"Method 2 - With database='neo4j': {result2['count']}")
            except Exception as e:
                logger.info(f"Method 2 failed: {e}")

            # Method 3: Show databases
            try:
                dbs = session.run("SHOW DATABASES").values()
                logger.info(f"📊 Available databases: {dbs}")
            except Exception as e:
                logger.info(f"SHOW DATABASES failed: {e}")

            # Method 4: Current database
            try:
                current_db = session.run("CALL db.info() YIELD name").single()
                logger.info(f"📊 Current database: {current_db['name']}")
            except Exception as e:
                logger.info(f"Current database check failed: {e}")

        # Test with explicit database connection
        logger.info("\n🔍 TESTING WITH EXPLICIT DATABASE CONNECTIONS:")

        # Test default database
        with driver.session(database="neo4j") as session:
            result_neo4j = session.run("MATCH (n) RETURN count(n) as count").single()
            logger.info(f"Database 'neo4j': {result_neo4j['count']} nodes")

        # Test system database
        try:
            with driver.session(database="system") as session:
                result_system = session.run(
                    "MATCH (n) RETURN count(n) as count"
                ).single()
                logger.info(f"Database 'system': {result_system['count']} nodes")
        except Exception as e:
            logger.info(f"System database test failed: {e}")

    except Exception as e:
        logger.error(f"❌ Debug failed: {str(e)}")
    finally:
        if "driver" in locals():
            driver.close()


if __name__ == "__main__":
    debug_auradb_access()
