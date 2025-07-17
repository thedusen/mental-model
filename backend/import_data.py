import os
import json
from config import cohere_client, get_db_session
from cohere.errors import TooManyRequestsError
import time

# --- Configuration ---
JSON_INPUT_PATH = '../data/themed_json' # Path to your new themed JSON files

def generate_embedding(text):
    """Generates an embedding for a given text using Cohere, with retry logic."""
    while True:
        try:
            response = cohere_client.embed(
                texts=[text], model="embed-english-v3.0", input_type="search_document"
            )
            return list(response.embeddings)[0]
        except TooManyRequestsError:
            print("Rate limit hit. Pausing for 60 seconds...")
            time.sleep(60)
            print("Retrying...")

def create_indexes():
    """Creates the necessary indexes in Neo4j."""
    with get_db_session() as session:
        session.run("CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (n:Entity) REQUIRE n.id IS UNIQUE")
        session.run("CREATE CONSTRAINT theme_name IF NOT EXISTS FOR (t:Theme) REQUIRE t.name IS UNIQUE")
        session.run("""
            CREATE VECTOR INDEX entity_embeddings IF NOT EXISTS
            FOR (n:Entity) ON (n.embedding)
            OPTIONS {indexConfig: {
                `vector.dimensions`: 1024,
                `vector.similarity_function`: 'cosine'
            }}
        """)
        print("Indexes and constraints ensured.")

def get_processed_node_ids():
    """Fetches the IDs of all nodes that already have an embedding."""
    with get_db_session() as session:
        result = session.run("MATCH (n:Entity) WHERE n.embedding IS NOT NULL RETURN n.id AS id")
        return {record["id"] for record in result}

def import_themed_json_files():
    """
    Reads themed JSON files, creates Entity and Theme nodes,
    and connects them with a BELONGS_TO relationship.
    Skips nodes that have already been processed.
    """
    print(f"Starting themed import from '{JSON_INPUT_PATH}'...")
    create_indexes()
    
    processed_ids = get_processed_node_ids()
    print(f"Found {len(processed_ids)} nodes already processed. They will be skipped.")
    
    with get_db_session() as session:
        for filename in os.listdir(JSON_INPUT_PATH):
            if filename.endswith('.json'):
                filepath = os.path.join(JSON_INPUT_PATH, filename)
                print(f"Processing themed file: {filename}")
                
                with open(filepath, 'r') as f:
                    batch_data = json.load(f)
                    for chunk_data in batch_data:
                        for node_type, nodes in chunk_data.items():
                            if isinstance(nodes, list):
                                for node in nodes:
                                    entity_id = node.get('name')
                                    
                                    # --- CHECK IF ALREADY PROCESSED ---
                                    if entity_id in processed_ids:
                                        print(f"  - Skipping already processed node: '{entity_id}'")
                                        continue
                                    
                                    description = node.get('description') or node.get('content', '')
                                    theme_name = node.get('theme')
                                    
                                    if not all([entity_id, description, theme_name]):
                                        print(f"Skipping item due to missing data: {node}")
                                        continue

                                    session.run("MERGE (t:Theme {name: $theme_name})", theme_name=theme_name)
                                    
                                    embedding = generate_embedding(description)
                                    entity_label = node_type.rstrip('s').capitalize()
                                    
                                    entity_query = """
                                    MERGE (e:Entity {id: $id})
                                    SET e:%s, e += $props, e.embedding = $embedding
                                    """ % (entity_label)
                                    
                                    props_to_set = node.copy()
                                    props_to_set.pop('name', None)
                                    
                                    session.run(entity_query, id=entity_id, props=props_to_set, embedding=embedding)
                                    
                                    rel_query = """
                                    MATCH (e:Entity {id: $entity_id})
                                    MATCH (t:Theme {name: $theme_name})
                                    MERGE (e)-[:BELONGS_TO]->(t)
                                    """
                                    session.run(rel_query, entity_id=entity_id, theme_name=theme_name)
                                    print(f"  - Imported '{entity_id}' and linked to Theme '{theme_name}'")

    print("Themed data import complete.")

if __name__ == "__main__":
    import_themed_json_files()
