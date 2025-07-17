import os
from dotenv import load_dotenv
from neo4j import GraphDatabase
import anthropic
import cohere

load_dotenv()

# CORRECTED: Initialize clients without arguments.
# The libraries will automatically pick up the API keys from your .env file.
anthropic_client = anthropic.Anthropic()
cohere_client = cohere.Client()

# CORRECTED: Add a check to ensure the environment variable is set.
# This satisfies the type checker that the value is not None.
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

if not NEO4J_URI:
    raise ValueError("NEO4J_URI environment variable not set")
if not NEO4J_USERNAME:
    raise ValueError("NEO4J_USERNAME environment variable not set")
if not NEO4J_PASSWORD:
    raise ValueError("NEO4J_PASSWORD environment variable not set")


neo4j_driver = GraphDatabase.driver(
    NEO4J_URI,
    auth=(NEO4J_USERNAME, NEO4J_PASSWORD)
)

def get_db_session():
    return neo4j_driver.session()