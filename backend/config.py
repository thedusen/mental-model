import os
from dotenv import load_dotenv
from neo4j import GraphDatabase
import anthropic
import cohere

# Load environment variables
load_dotenv()

# Initialize clients
anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
cohere_client = cohere.ClientV2(os.getenv("COHERE_API_KEY"))  # V2 for latest features

# Initialize Neo4j connection
neo4j_driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD"))
)

def get_db_session():
    return neo4j_driver.session()