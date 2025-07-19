import asyncio
import logging
from datetime import datetime
from .config import get_db_session

logger = logging.getLogger(__name__)

class DatabaseKeepWarm:
    def __init__(self, interval_minutes=10):
        self.interval_minutes = interval_minutes
        self.running = False
        
    async def ping_database(self):
        """Simple database ping to prevent cold starts"""
        try:
            with get_db_session() as session:
                result = session.run("RETURN datetime() as current_time")
                record = result.single()
                if record:
                    logger.info(f"Database ping successful at {record['current_time']}")
                    return True
        except Exception as e:
            logger.error(f"Database ping failed: {e}")
            return False
        
    async def start_keep_warm_loop(self):
        """Background task to keep database warm"""
        self.running = True
        logger.info(f"Starting database keep-warm service (ping every {self.interval_minutes} minutes)")
        
        while self.running:
            try:
                await self.ping_database()
                # Wait for the specified interval
                await asyncio.sleep(self.interval_minutes * 60)  # Convert minutes to seconds
            except Exception as e:
                logger.error(f"Keep-warm loop error: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying
                
    async def stop_keep_warm_loop(self):
        """Stop the keep-warm service"""
        self.running = False
        logger.info("Database keep-warm service stopped")

# Global instance
keep_warm_service = DatabaseKeepWarm(interval_minutes=10) 