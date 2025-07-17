import os
from dotenv import load_dotenv
from neo4j import GraphDatabase
import anthropic
import cohere

load_dotenv()

anthropic_client = anthropic.Anthropic()
cohere_client = cohere.Client()

NEO4J_URI = os.getenv("NEO4J_URI")
if not NEO4J_URI:
    raise ValueError("NEO4J_URI environment variable not set")

neo4j_driver = GraphDatabase.driver(
    NEO4J_URI,
    auth=(os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD"))
)

def get_db_session():
    return neo4j_driver.session()
