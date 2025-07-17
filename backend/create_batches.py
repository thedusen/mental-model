import os
import json
import math

# --- Configuration ---
JSON_INPUT_PATH = '../data/json'
BATCH_OUTPUT_PATH = '../data/batched_for_theming'
BATCH_SIZE = 10

def create_json_batches():
    """
    Reads all JSON files from the input path, groups their contents
    into batches, and writes them to new files in the output directory.
    """
    print(f"Starting to create batches from: {JSON_INPUT_PATH}")

    # Create the output directory if it doesn't exist
    os.makedirs(BATCH_OUTPUT_PATH, exist_ok=True)

    # Get a sorted list of all JSON files to ensure consistent ordering
    all_files = sorted([f for f in os.listdir(JSON_INPUT_PATH) if f.endswith('.json')])

    if not all_files:
        print("No JSON files found in the input directory.")
        return

    num_batches = math.ceil(len(all_files) / BATCH_SIZE)
    print(f"Found {len(all_files)} files, creating {num_batches} batches of size {BATCH_SIZE}...")

    for i in range(num_batches):
        start_index = i * BATCH_SIZE
        end_index = start_index + BATCH_SIZE
        batch_files = all_files[start_index:end_index]

        batch_content = []
        for filename in batch_files:
            filepath = os.path.join(JSON_INPUT_PATH, filename)
            with open(filepath, 'r') as f:
                try:
                    # Add the original filename to the data before appending
                    data = json.load(f)
                    data['source_chunk_filename'] = filename
                    batch_content.append(data)
                except json.JSONDecodeError:
                    print(f"  - Warning: Could not decode JSON from {filename}, skipping.")

        # Write the batch to a new file
        batch_filename = f'batch_{i+1}.json'
        output_filepath = os.path.join(BATCH_OUTPUT_PATH, batch_filename)
        with open(output_filepath, 'w') as f:
            json.dump(batch_content, f, indent=2)

        print(f"  - Created {batch_filename} with {len(batch_files)} files.")

    print(f"\nBatch creation complete. Files are located in: {BATCH_OUTPUT_PATH}")

if __name__ == "__main__":
    create_json_batches()