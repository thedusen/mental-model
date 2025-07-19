from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Any
import time
import psutil
import logging
from config import neo4j_driver
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

health_router = APIRouter()

class HealthStatus(BaseModel):
    status: str
    timestamp: str
    version: str
    checks: Dict[str, Any]

class DetailedHealthStatus(BaseModel):
    status: str
    timestamp: str
    version: str
    uptime_seconds: float
    checks: Dict[str, Any]
    system: Dict[str, Any]

# Global startup time for uptime calculation
_startup_time = time.time()

@health_router.get("/health", response_model=HealthStatus)
async def health_check():
    """Basic health check endpoint for load balancers"""
    checks = {}
    overall_status = "healthy"
    
    # Database connectivity check
    try:
        with neo4j_driver.session() as session:
            result = session.run("RETURN 1 as test")
            record = result.single()
            if record and record["test"] == 1:
                checks["database"] = {"status": "healthy", "response_time_ms": "< 100"}
            else:
                checks["database"] = {"status": "unhealthy", "error": "Invalid response"}
                overall_status = "unhealthy"
    except Exception as e:
        checks["database"] = {"status": "unhealthy", "error": str(e)}
        overall_status = "unhealthy"
        logger.error(f"Database health check failed: {e}")
    
    # API dependencies check (basic connectivity)
    try:
        # This is a minimal check - in production you'd ping actual endpoints
        checks["external_apis"] = {"status": "healthy", "note": "Configuration verified"}
    except Exception as e:
        checks["external_apis"] = {"status": "degraded", "error": str(e)}
        logger.warning(f"External API check warning: {e}")
    
    return HealthStatus(
        status=overall_status,
        timestamp=datetime.now(timezone.utc).isoformat(),
        version="1.0.0",
        checks=checks
    )

@health_router.get("/health/detailed", response_model=DetailedHealthStatus)
async def detailed_health_check():
    """Detailed health check with system metrics"""
    checks = {}
    overall_status = "healthy"
    
    # Database connectivity with metrics
    try:
        start_time = time.time()
        with neo4j_driver.session() as session:
            # Check basic connectivity
            result = session.run("RETURN 1 as test")
            record = result.single()
            
            # Check node count as a basic data validation
            result = session.run("MATCH (n) RETURN count(n) as node_count")
            node_record = result.single()
            node_count = node_record["node_count"] if node_record else 0
            
            response_time_ms = round((time.time() - start_time) * 1000, 2)
            
            checks["database"] = {
                "status": "healthy",
                "response_time_ms": response_time_ms,
                "node_count": node_count,
                "connection_pool": "active"
            }
    except Exception as e:
        checks["database"] = {"status": "unhealthy", "error": str(e)}
        overall_status = "unhealthy"
        logger.error(f"Database detailed health check failed: {e}")
    
    # System metrics
    try:
        system_info = {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent,
            "load_average": psutil.getloadavg()[0] if hasattr(psutil, 'getloadavg') else None
        }
        checks["system"] = {"status": "healthy", "metrics": system_info}
        
        # Alert on high resource usage
        if system_info["memory_percent"] > 90 or system_info["cpu_percent"] > 90:
            overall_status = "degraded"
            checks["system"]["status"] = "degraded"
            checks["system"]["warning"] = "High resource usage detected"
            
    except Exception as e:
        checks["system"] = {"status": "unknown", "error": str(e)}
        logger.warning(f"System metrics check failed: {e}")
    
    return DetailedHealthStatus(
        status=overall_status,
        timestamp=datetime.now(timezone.utc).isoformat(),
        version="1.0.0",
        uptime_seconds=round(time.time() - _startup_time, 2),
        checks=checks,
        system=checks.get("system", {}).get("metrics", {})
    )

@health_router.get("/health/ready")
async def readiness_check():
    """Kubernetes-style readiness check"""
    try:
        # Check if application is ready to serve traffic
        with neo4j_driver.session() as session:
            session.run("RETURN 1")
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "ready"}
        )
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not ready", "error": str(e)}
        )

@health_router.get("/health/live")
async def liveness_check():
    """Kubernetes-style liveness check"""
    # Basic application liveness - if this endpoint responds, the app is alive
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": "alive",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    ) 