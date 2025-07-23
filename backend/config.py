import os
from dotenv import load_dotenv
from neo4j import GraphDatabase
import anthropic
import cohere
from zep_cloud.client import Zep

load_dotenv(override=True)

anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
cohere_client = cohere.Client(api_key=os.getenv("COHERE_API_KEY"))

# Zep configuration - graceful fallback for CI/testing environments
ZEP_API_URL = os.getenv("ZEP_API_URL", "https://api.getzep.com")
ZEP_API_KEY = os.getenv("ZEP_API_KEY")

# Initialize Zep client if API key is available
zep_client = None
if ZEP_API_KEY:
    try:
        zep_client = Zep(base_url=ZEP_API_URL, api_key=ZEP_API_KEY)
    except Exception as e:
        print(f"Warning: Failed to initialize Zep client: {e}")
        zep_client = None
else:
    print("Warning: ZEP_API_KEY not set - Zep functionality will be disabled")

NEO4J_URI = os.getenv("NEO4J_URI")
if not NEO4J_URI:
    raise ValueError("NEO4J_URI environment variable not set")

neo4j_driver = GraphDatabase.driver(
    NEO4J_URI, auth=(os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD"))
)


def get_db_session():
    return neo4j_driver.session()
