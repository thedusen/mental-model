#!/usr/bin/env python3
"""
Final categorization script for remaining uncategorized nodes using enhanced keyword analysis.
"""

from config import get_db_session
import re

def final_categorization():
    """Apply enhanced categorization to remaining uncategorized nodes."""
    
    # Enhanced categorization rules with more keywords and context
    categorization_rules = {
        'VALUE FRAMEWORK': [
            'value', 'principle', 'belief', 'ethic', 'foundation', 'core', 'integrity', 
            'trust', 'respect', 'honesty', 'responsibility', 'family', 'parent', 'model', 
            'admiration', 'purpose', 'meaning', 'mission', 'vision', 'commitment', 'loyalty',
            'dedication', 'devotion', 'priority', 'philosophy', 'conviction', 'standard',
            'ideal', 'moral', 'character', 'authenticity', 'genuine', 'sincere'
        ],
        'COGNITIVE TENSIONS': [
            'tension', 'conflict', 'balance', 'trade-off', 'dilemma', 'challenge',
            'complexity', 'paradox', 'competing', 'opposing', 'struggle', 'difficulty',
            'problem', 'issue', 'concern', 'worry', 'stress', 'pressure', 'contradiction',
            'ambiguity', 'uncertainty', 'confusion', 'disagreement', 'debate', 'argument',
            'resistance', 'friction', 'obstacle', 'barrier', 'constraint', 'limitation'
        ],
        'DECISION ARCHITECTURE': [
            'decision', 'choose', 'selection', 'analysis', 'evaluation', 'assessment',
            'criteria', 'process', 'method', 'approach', 'strategy', 'planning',
            'systematic', 'structured', 'framework', 'model', 'logic', 'reasoning',
            'judgment', 'consideration', 'deliberation', 'calculation', 'weighing',
            'comparison', 'option', 'alternative', 'solution', 'recommendation'
        ],
        'ADAPTIVE CORE': [
            'adapt', 'change', 'evolution', 'growth', 'learning', 'development',
            'flexible', 'responsive', 'dynamic', 'adjustment', 'modification',
            'improvement', 'transformation', 'progression', 'advancement', 'iteration',
            'refinement', 'enhancement', 'upgrade', 'innovation', 'experiment',
            'pivot', 'shift', 'transition', 'evolve', 'mature', 'develop'
        ],
        'ENERGY PATTERNS': [
            'energy', 'motivation', 'drive', 'passion', 'enthusiasm', 'engagement',
            'stimulation', 'activation', 'excitement', 'intensity', 'vigor',
            'momentum', 'pace', 'rhythm', 'flow', 'dynamics', 'inspiration',
            'spark', 'fuel', 'charge', 'boost', 'lift', 'invigorate', 'animate',
            'revitalize', 'energize', 'motivate', 'inspire', 'excite'
        ]
    }
    
    with get_db_session() as session:
        # Get remaining uncategorized nodes with more context
        result = session.run("""
            MATCH (e:Entity) 
            WHERE e.category IS NULL 
            RETURN e.id as id, e.description as description, e.theme as theme,
                   e.context as context, e.content as content
        """)
        
        uncategorized_nodes = list(result)
        print(f"Processing {len(uncategorized_nodes)} remaining uncategorized nodes")
        
        categorization_counts = {}
        updated_count = 0
        
        for node in uncategorized_nodes:
            node_id = node['id']
            description = node['description'] or ''
            theme = node['theme'] or ''
            context = node['context'] or ''
            content = node['content'] or ''
            
            # Combine all available text for analysis
            text_to_analyze = f"{node_id} {description} {theme} {context} {content}".lower()
            
            # Score each category based on keyword matches
            category_scores = {}
            for category, keywords in categorization_rules.items():
                score = 0
                for keyword in keywords:
                    # Count occurrences of keyword (case insensitive, word boundaries)
                    matches = len(re.findall(r'\b' + re.escape(keyword.lower()) + r'\b', text_to_analyze))
                    score += matches
                    
                    # Give extra weight for matches in node ID or description
                    if keyword.lower() in node_id.lower():
                        score += 2
                    if keyword.lower() in description.lower():
                        score += 1.5
                
                category_scores[category] = score
            
            # Assign to category with highest score (minimum score of 1)
            best_category = max(category_scores.items(), key=lambda x: x[1])
            if best_category[1] >= 1:  # Require at least 1 keyword match
                category = best_category[0]
                
                # Update the node in the database
                session.run("""
                    MATCH (e:Entity {id: $id})
                    SET e.category = $category
                """, id=node_id, category=category)
                
                categorization_counts[category] = categorization_counts.get(category, 0) + 1
                updated_count += 1
                
                print(f"Categorized '{node_id}' as {category} (score: {best_category[1]})")
        
        print(f"\nFinal categorization complete!")
        print(f"Updated {updated_count} additional nodes:")
        for category, count in sorted(categorization_counts.items()):
            print(f"  {category}: +{count} nodes")
        
        # Show final distribution
        result = session.run("""
            MATCH (e:Entity) 
            RETURN 
                CASE WHEN e.category IS NULL THEN 'Uncategorized' ELSE e.category END as category,
                count(*) as count 
            ORDER BY count DESC
        """)
        
        print(f"\nFinal category distribution:")
        total_categorized = 0
        total_nodes = 0
        for record in result:
            count = record['count']
            total_nodes += count
            if record['category'] != 'Uncategorized':
                total_categorized += count
            print(f"  {record['category']}: {count}")
        
        categorization_percentage = (total_categorized / total_nodes) * 100
        print(f"\nCategorization success: {total_categorized}/{total_nodes} nodes ({categorization_percentage:.1f}%)")

if __name__ == "__main__":
    final_categorization() 