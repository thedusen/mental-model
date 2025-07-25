import os
import logging
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

if ZEP_API_KEY:
    try:
        logger.info(f"Initializing Zep client with URL: {ZEP_API_URL}")
        zep_client = Zep(base_url=ZEP_API_URL, api_key=ZEP_API_KEY)

        # Test connection by attempting to create a test operation
        try:
            test_response = zep_client.user.list_ordered(page_size=1)
            zep_health_status["connected"] = True
            zep_health_status["initialized_at"] = str(
                os.getenv("DEPLOY_TIME", "unknown")
            )
            logger.info("Zep client initialized successfully and connection verified")
        except Exception as test_error:
            logger.warning(
                f"Zep client initialized but connection test failed: {test_error}"
            )
            zep_health_status["last_error"] = str(test_error)

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
