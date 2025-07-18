#!/usr/bin/env python3
"""
Script to categorize uncategorized Entity nodes based on keywords in their descriptions and themes.
"""

from config import get_db_session
import re

def categorize_uncategorized_nodes():
    """Categorize nodes that don't have a category set."""
    
    # Define categorization rules based on keywords
    categorization_rules = {
        'VALUE FRAMEWORK': [
            'value', 'framework', 'principle', 'belief', 'foundation', 'core', 'ethic', 
            'motivation', 'purpose', 'meaning', 'integrity', 'trust', 'respect',
            'honesty', 'responsibility', 'family', 'parent', 'model', 'admiration'
        ],
        'COGNITIVE TENSIONS': [
            'tension', 'conflict', 'balance', 'trade-off', 'dilemma', 'challenge',
            'complexity', 'paradox', 'competing', 'opposing', 'struggle', 'difficulty',
            'problem', 'issue', 'concern', 'worry', 'stress', 'pressure'
        ],
        'DECISION ARCHITECTURE': [
            'decision', 'choose', 'selection', 'analysis', 'evaluation', 'assessment',
            'criteria', 'process', 'method', 'approach', 'strategy', 'planning',
            'systematic', 'structured', 'framework', 'model', 'logic', 'reasoning'
        ],
        'ADAPTIVE CORE': [
            'adapt', 'change', 'evolution', 'growth', 'learning', 'development',
            'flexible', 'responsive', 'dynamic', 'adjustment', 'modification',
            'improvement', 'transformation', 'progression', 'advancement'
        ],
        'ENERGY PATTERNS': [
            'energy', 'motivation', 'drive', 'passion', 'enthusiasm', 'engagement',
            'stimulation', 'activation', 'excitement', 'intensity', 'vigor',
            'momentum', 'pace', 'rhythm', 'flow', 'dynamics'
        ]
    }
    
    with get_db_session() as session:
        # Get all uncategorized nodes
        result = session.run("""
            MATCH (e:Entity) 
            WHERE e.category IS NULL 
            RETURN e.id as id, e.description as description, e.theme as theme
        """)
        
        uncategorized_nodes = list(result)
        print(f"Found {len(uncategorized_nodes)} uncategorized nodes")
        
        categorization_counts = {}
        updated_count = 0
        
        for node in uncategorized_nodes:
            node_id = node['id']
            description = node['description'] or ''
            theme = node['theme'] or ''
            
            # Combine description and theme for analysis
            text_to_analyze = f"{description} {theme}".lower()
            
            # Score each category based on keyword matches
            category_scores = {}
            for category, keywords in categorization_rules.items():
                score = 0
                for keyword in keywords:
                    # Count occurrences of keyword (case insensitive)
                    score += len(re.findall(r'\b' + re.escape(keyword.lower()) + r'\b', text_to_analyze))
                category_scores[category] = score
            
            # Assign to category with highest score (if any matches found)
            best_category = max(category_scores.items(), key=lambda x: x[1])
            if best_category[1] > 0:  # Only assign if we found matching keywords
                category = best_category[0]
                
                # Update the node in the database
                session.run("""
                    MATCH (e:Entity {id: $id})
                    SET e.category = $category
                """, id=node_id, category=category)
                
                categorization_counts[category] = categorization_counts.get(category, 0) + 1
                updated_count += 1
                
                print(f"Categorized '{node_id}' as {category} (score: {best_category[1]})")
        
        print(f"\nCategorization complete!")
        print(f"Updated {updated_count} nodes:")
        for category, count in sorted(categorization_counts.items()):
            print(f"  {category}: {count} nodes")
        
        # Show remaining uncategorized count
        result = session.run("MATCH (e:Entity) WHERE e.category IS NULL RETURN count(*) as count")
        remaining_record = result.single()
        remaining = remaining_record['count'] if remaining_record else 0
        print(f"\nRemaining uncategorized: {remaining} nodes")

if __name__ == "__main__":
    categorize_uncategorized_nodes() 