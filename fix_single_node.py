import json
from config import cohere_client, get_db_session
from cohere.errors import TooManyRequestsError
import time

# --- Manually define the node to fix here ---
node_to_fix = {
    "name": "Brian's Business-First Mental Model Development",
    "content": "Dan wants warehouse manager Brian to 'recognize' that 'acting in the best interest of the business is the best way to act.' Brian 'tends to put the customer first, regardless of the financial implications,' so Dan teaches balance: 'It's not always about the financial decision. It's not always about the customer. There's a balance that needs to be struck.' Dan also notes Brian 'doesn't ask more of himself or the team' but finds this harder to address.",
    "source": "Interview Transcript",
    "timestamp": "12:46",
    "theme": "Business-First Balance and Recognition",
    "source_chunk": "mental_model_chunk_35.json"
}
# This node is an 'Example', so we'll set the label manually
NODE_TYPE_LABEL = "Example"


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

def fix_single_node():
    """
    Imports a single, specified node into the database, including its
    embedding and relationship to its theme.
    """
    print(f"Starting import for single node: '{node_to_fix.get('name')}'")
    
    with get_db_session() as session:
        entity_id = node_to_fix.get('name')
        description = node_to_fix.get('description') or node_to_fix.get('content', '')
        theme_name = node_to_fix.get('theme')

        if not all([entity_id, description, theme_name]):
            print(f"Cannot process node, required data is missing: {node_to_fix}")
            return

        # 1. Ensure the Theme node exists
        session.run("MERGE (t:Theme {name: $theme_name})", theme_name=theme_name)
        print(f"  - Ensured Theme '{theme_name}' exists.")

        # 2. Generate embedding and create the Entity node
        embedding = generate_embedding(description)
        
        entity_query = """
        MERGE (e:Entity {id: $id})
        SET e:%s, e += $props, e.embedding = $embedding
        """ % (NODE_TYPE_LABEL)
        
        props_to_set = node_to_fix.copy()
        props_to_set.pop('name', None)
        
        session.run(entity_query, id=entity_id, props=props_to_set, embedding=embedding)
        print(f"  - Created/Updated Entity node '{entity_id}'.")

        # 3. Create the relationship to its Theme
        rel_query = """
        MATCH (e:Entity {id: $entity_id})
        MATCH (t:Theme {name: $theme_name})
        MERGE (e)-[:BELONGS_TO]->(t)
        """
        session.run(rel_query, entity_id=entity_id, theme_name=theme_name)
        print(f"  - Linked '{entity_id}' to Theme '{theme_name}'.")

    print("\nSingle node import complete.")

if __name__ == "__main__":
    fix_single_node()
