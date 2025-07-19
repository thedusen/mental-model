import os
import json
import time
from config import cohere_client, get_db_session
from cohere.errors import TooManyRequestsError

JSON_DATA_PATH = '../data/json'

def generate_embedding(text):
    """
    Generates an embedding for a given text using Cohere.
    Includes retry logic for rate limiting.
    """
    while True:
        try:
            # CORRECTED: Specify embedding_types and access the .float attribute.
            response = cohere_client.embed(
                texts=[text], model="embed-english-v3.0", input_type="search_document", embedding_types=["float"]
            )
            return response.embeddings.float[0]  # type: ignore
        except TooManyRequestsError:
            print("Rate limit hit. Pausing for 60 seconds...")
            time.sleep(60)
            print("Retrying...")

def create_vector_index():
    with get_db_session() as session:
        session.run("""
            CREATE VECTOR INDEX entity_embeddings IF NOT EXISTS
            FOR (n:Entity) ON (n.embedding)
            OPTIONS {indexConfig: {
                `vector.dimensions`: 1024,
                `vector.similarity_function`: 'cosine'
            }}
        """)
        print("Vector index ensured.")

def import_json_files():
    print(f"Starting import from '{JSON_DATA_PATH}'...")
    create_vector_index()
    with get_db_session() as session:
        for filename in os.listdir(JSON_DATA_PATH):
            if filename.endswith('.json'):
                filepath = os.path.join(JSON_DATA_PATH, filename)
                print(f"Processing file: {filename}")
                with open(filepath, 'r') as f:
                    data = json.load(f)
                    for key, items in data.items():
                        if isinstance(items, list):
                            label = key.rstrip('s').capitalize()
                            for item in items:
                                entity_id = item.get('name')
                                description = item.get('description') or item.get('content', '')
                                if not entity_id or not description:
                                    continue
                                
                                # This function will now automatically handle rate limits
                                embedding = generate_embedding(description)
                                
                                # CORRECTED: Use apoc.merge.node for safer dynamic labels.
                                query = """
                                CALL apoc.merge.node($labels, {id: $id}, $props, {})
                                YIELD node
                                SET node.embedding = $embedding
                                """
                                props_to_set = item.copy()
                                props_to_set.pop('name', None)
                                
                                # Pass the dynamic labels as a list parameter.
                                session.run(query, labels=['Entity', label], id=entity_id, props=props_to_set, embedding=embedding)
                                print(f"  - Imported '{entity_id}' as a {label} node.")
    print("Data import complete.")

if __name__ == "__main__":
    import_json_files()