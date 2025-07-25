import os
import logging
from typing import Tuple
from datetime import datetime
from dotenv import load_dotenv
from neo4j import GraphDatabase
import anthropic
import cohere
from zep_cloud.client import Zep

load_dotenv(override=True)

# Configure logging for production debugging
logger = logging.getLogger(__name__)

anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
cohere_client = cohere.Client(api_key=os.getenv("COHERE_API_KEY"))

# Zep configuration - graceful fallback for CI/testing environments
ZEP_API_URL = os.getenv("ZEP_API_URL", "https://api.getzep.com")
ZEP_API_KEY = os.getenv("ZEP_API_KEY")

# Initialize Zep client if API key is available
zep_client = None
zep_health_status = {"connected": False, "last_error": None, "initialized_at": None}


def validate_zep_api_key(api_key: str) -> Tuple[bool, str]:
    """Validate Zep API key format"""
    if not api_key:
        return False, "API key is empty"

    if not (api_key.startswith("zep_") or api_key.startswith("z_")):
        return False, "API key should start with 'zep_' or 'z_'"

    if len(api_key) < 20:
        return False, f"API key appears too short ({len(api_key)} characters)"

    if "\n" in api_key or "\r" in api_key:
        return False, "API key contains newline characters"

    if api_key.startswith(" ") or api_key.endswith(" "):
        return False, "API key has leading/trailing whitespace"

    return True, "API key format is valid"


if ZEP_API_KEY:
    # First validate API key format
    key_valid, key_message = validate_zep_api_key(ZEP_API_KEY)

    if not key_valid:
        logger.error(f"Invalid Zep API key format: {key_message}")
        zep_health_status["last_error"] = f"Invalid API key format: {key_message}"
        zep_client = None
    else:
        try:
            logger.info(f"Initializing Zep client with URL: {ZEP_API_URL}")
            logger.info(f"API key format validation: {key_message}")
            zep_client = Zep(base_url=ZEP_API_URL, api_key=ZEP_API_KEY)

            # Test connection by attempting to create a test operation
            try:
                # Use user.list() instead of list_ordered() which may not exist
                test_response = zep_client.user.list(limit=1)
                zep_health_status["connected"] = True
                zep_health_status["initialized_at"] = str(
                    os.getenv("DEPLOY_TIME", datetime.now().isoformat())
                )
                logger.info(
                    "Zep client initialized successfully and connection verified"
                )

                # Log user count for debugging
                if hasattr(test_response, "users") and test_response.users:
                    logger.info(
                        f"Found {len(test_response.users)} existing users in Zep"
                    )
                else:
                    logger.info(
                        "No existing users found in Zep (expected for new projects)"
                    )

            except Exception as test_error:
                error_msg = str(test_error)
                logger.warning(
                    f"Zep client initialized but connection test failed: {error_msg}"
                )
                zep_health_status["last_error"] = error_msg

                # Provide specific guidance based on error
                if "401" in error_msg or "unauthorized" in error_msg.lower():
                    logger.error("🚨 CRITICAL: Zep API key is invalid or expired!")
                    logger.error(
                        "   -> Generate a new API key from https://cloud.getzep.com"
                    )
                    logger.error("   -> Update ZEP_API_KEY environment variable")
                elif "403" in error_msg or "forbidden" in error_msg.lower():
                    logger.error("🚨 CRITICAL: Zep API key lacks required permissions!")
                    logger.error("   -> Check API key scope in Zep dashboard")

        except Exception as e:
            logger.error(f"Failed to initialize Zep client: {e}")
            zep_health_status["last_error"] = str(e)
            zep_client = None
else:
    logger.warning("ZEP_API_KEY not set - Zep functionality will be disabled")
    zep_health_status["last_error"] = "ZEP_API_KEY environment variable not set"

NEO4J_URI = os.getenv("NEO4J_URI")
if not NEO4J_URI:
    raise ValueError("NEO4J_URI environment variable not set")

neo4j_driver = GraphDatabase.driver(
    NEO4J_URI, auth=(os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD"))
)


def get_db_session():
    return neo4j_driver.session()


def validate_production_environment():
    """
    Validate that all required environment variables are set for production deployment
    Returns a dict with validation results and recommendations
    """
    validation_results = {
        "valid": True,
        "warnings": [],
        "errors": [],
        "recommendations": [],
    }

    # Critical environment variables
    critical_vars = {
        "NEO4J_URI": os.getenv("NEO4J_URI"),
        "NEO4J_USERNAME": os.getenv("NEO4J_USERNAME"),
        "NEO4J_PASSWORD": os.getenv("NEO4J_PASSWORD"),
        "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY"),
        "COHERE_API_KEY": os.getenv("COHERE_API_KEY"),
    }

    # Optional but recommended variables
    optional_vars = {
        "ZEP_API_KEY": os.getenv("ZEP_API_KEY"),
        "ZEP_API_URL": os.getenv("ZEP_API_URL"),
    }

    # Check critical variables
    for var_name, var_value in critical_vars.items():
        if not var_value:
            validation_results["errors"].append(
                f"Missing critical environment variable: {var_name}"
            )
            validation_results["valid"] = False
        elif var_name.endswith("_KEY") and len(var_value) < 10:
            validation_results["warnings"].append(
                f"Environment variable {var_name} appears to be too short"
            )

    # Check optional variables
    for var_name, var_value in optional_vars.items():
        if not var_value:
            if var_name == "ZEP_API_KEY":
                validation_results["warnings"].append(
                    "ZEP_API_KEY not set - user personalization features will be disabled"
                )
            elif var_name == "ZEP_API_URL":
                validation_results["recommendations"].append(
                    "ZEP_API_URL not set - using default https://api.getzep.com"
                )

    # Environment-specific checks
    environment = os.getenv("ENVIRONMENT", "development").lower()
    if environment in ["production", "prod"]:
        # Production-specific validations
        if os.getenv("NEO4J_URI", "").startswith("bolt://localhost"):
            validation_results["errors"].append(
                "Production environment should not use localhost Neo4j"
            )
            validation_results["valid"] = False

        if not os.getenv("CORS_ORIGINS"):
            validation_results["warnings"].append(
                "CORS_ORIGINS not set - this may cause frontend connectivity issues"
            )

        # Check for development indicators
        if os.getenv("DEBUG", "").lower() == "true":
            validation_results["recommendations"].append(
                "DEBUG mode should be disabled in production"
            )

    # Zep-specific validations
    if zep_client:
        validation_results["recommendations"].append(
            "Zep client initialized successfully"
        )
    elif ZEP_API_KEY:
        validation_results["warnings"].append(
            "Zep API key provided but client initialization failed"
        )

    return validation_results


# Run validation on import (only log, don't fail)
try:
    validation = validate_production_environment()
    if not validation["valid"]:
        logger.error("Environment validation failed:")
        for error in validation["errors"]:
            logger.error(f"  - {error}")

    if validation["warnings"]:
        logger.warning("Environment validation warnings:")
        for warning in validation["warnings"]:
            logger.warning(f"  - {warning}")

    if validation["recommendations"]:
        logger.info("Environment recommendations:")
        for rec in validation["recommendations"]:
            logger.info(f"  - {rec}")

except Exception as e:
    logger.error(f"Failed to run environment validation: {e}")
