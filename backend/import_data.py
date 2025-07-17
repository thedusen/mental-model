import os
import json
from config import cohere_client, get_db_session

JSON_DATA_PATH = '../data/json'

def generate_embedding(text):
    response = cohere_client.embed(
        texts=[text], model="embed-english-v3.0", input_type="search_document"
    )
    return response.embeddings[0]

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
                                embedding = generate_embedding(description)
                                query = f"MERGE (e:Entity:{label} {{id: $id}}) SET e += $props, e.embedding = $embedding"
                                props_to_set = item.copy()
                                props_to_set.pop('name', None)
                                session.run(query, id=entity_id, props=props_to_set, embedding=embedding)
                                print(f"  - Imported '{entity_id}' as a {label} node.")
    print("Data import complete.")

if __name__ == "__main__":
    import_json_files()
