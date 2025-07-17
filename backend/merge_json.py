import os
import json
from collections import defaultdict

# --- Configuration ---
# CORRECTED: This now points to your themed data directory.
JSON_INPUT_PATH = '../data/themed_json'
JSON_OUTPUT_PATH = '../data/master_knowledge.json'

def merge_json_files():
    """
    Reads all JSON files from the themed_json directory, merges their contents
    based on top-level keys, and writes to a single master file.
    """
    merged_data = defaultdict(list)

    print(f"Starting merge from directory: {JSON_INPUT_PATH}")

    if not os.path.isdir(JSON_INPUT_PATH):
        print(f"Error: Input directory not found at '{JSON_INPUT_PATH}'")
        print("Please make sure you have run the theming process and saved the output first.")
        return

    for filename in os.listdir(JSON_INPUT_PATH):
        if filename.endswith('.json'):
            filepath = os.path.join(JSON_INPUT_PATH, filename)
            print(f"  - Processing {filename}...")

            with open(filepath, 'r') as f:
                try:
                    # The themed files contain a list of objects
                    batch_data = json.load(f)
                    for chunk_data in batch_data:
                        for key, items in chunk_data.items():
                            if key in ['principles', 'patterns', 'examples']:
                                merged_data[key].extend(items)
                except json.JSONDecodeError:
                    print(f"    Error: Could not decode JSON from {filename}, skipping.")

    if not merged_data:
        print("\nWarning: No data was merged. The master file will not be created or modified.")
        return

    with open(JSON_OUTPUT_PATH, 'w') as f:
        json.dump(merged_data, f, indent=2)

    print(f"\nMerge complete. All data saved to '{JSON_OUTPUT_PATH}'")
    print(f"Discovered top-level keys: {list(merged_data.keys())}")

if __name__ == "__main__":
    merge_json_files()

