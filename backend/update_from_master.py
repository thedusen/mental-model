#!/usr/bin/env python3
"""
Script to update Entity node categories from the master_knowledge.json file.
"""

import json
from config import get_db_session

def update_categories_from_master():
    """Update categories from master_knowledge.json file."""
    
    with open('../data/master_knowledge.json', 'r') as f:
        master_data = json.load(f)
    
    # Extract all categorized principles from master file
    categorized_items = {}
    
    for group in master_data:
        if 'principles' in group:
            for principle in group['principles']:
                name = principle.get('name')
                category = principle.get('category')
                if name and category:
                    categorized_items[name] = category
    
    print(f"Found {len(categorized_items)} categorized items in master file")
    
    # Update database
    with get_db_session() as session:
        updated_count = 0
        
        for name, category in categorized_items.items():
            # Check if this entity exists and update its category
            result = session.run("""
                MATCH (e:Entity {id: $name})
                SET e.category = $category
                RETURN e.id as id
            """, name=name, category=category)
            
            if result.single():
                updated_count += 1
                print(f"Updated: {name} -> {category}")
        
        print(f"\nUpdated {updated_count} entities from master file")
        
        # Show new distribution
        result = session.run("""
            MATCH (e:Entity) 
            RETURN 
                CASE WHEN e.category IS NULL THEN 'Uncategorized' ELSE e.category END as category,
                count(*) as count 
            ORDER BY count DESC
        """)
        
        print("\nNew category distribution:")
        for record in result:
            print(f"  {record['category']}: {record['count']}")

if __name__ == "__main__":
    update_categories_from_master() 