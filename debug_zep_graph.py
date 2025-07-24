#!/usr/bin/env python3
"""
Debug Zep Graph API Functionality
"""

import sys
sys.path.append('backend')

import json
import uuid
from zep_memory import zep_service

async def debug_zep_graph():
    print("🔍 Debugging Zep Graph API...")
    
    if not zep_service.enabled:
        print("❌ Zep is not enabled")
        return
    
    test_user_id = f"debug_user_{uuid.uuid4().hex[:8]}"
    print(f"Test user ID: {test_user_id}")
    
    try:
        # Step 1: Ensure user exists
        print("\n1️⃣ Creating Zep user...")
        user = zep_service.manager.ensure_user_exists(test_user_id)
        print(f"✅ User created: {user}")
        
        # Step 2: Try basic graph add
        print("\n2️⃣ Testing basic graph.add()...")
        test_data = {"test": "data", "entity_id": "test_entity"}
        
        result = zep_service.client.graph.add(
            user_id=test_user_id,
            data=json.dumps(test_data),
            type="json"
        )
        print(f"✅ Graph add result: {result}")
        
        # Step 3: Wait and try to retrieve
        import asyncio
        print("\n3️⃣ Waiting and retrieving...")
        await asyncio.sleep(3)
        
        # Try to get nodes
        nodes = zep_service.client.graph.node.get_by_user_id(user_id=test_user_id)
        print(f"📊 Retrieved {len(nodes)} nodes")
        
        for i, node in enumerate(nodes):
            print(f"   Node {i+1}: {type(node)}")
            print(f"      UUID: {getattr(node, 'uuid_', 'N/A')}")
            print(f"      Name: {getattr(node, 'name', 'N/A')}")
            print(f"      Summary: {getattr(node, 'summary', 'N/A')}")
            print(f"      Labels: {getattr(node, 'labels', 'N/A')}")
            print(f"      All attributes: {[attr for attr in dir(node) if not attr.startswith('_')]}")
            
            # Check if there's any way to access the raw data
            for attr in ['data', 'content', 'json', 'attributes']:
                value = getattr(node, attr, None)
                if value:
                    print(f"      {attr}: {value}")
            
            # Try to get back to the original content
            try:
                # Maybe we need to look at related documents?
                print(f"      Trying to access node internals...")
            except Exception as e:
                print(f"      Error accessing internals: {e}")
            
        # Step 4: Test our questionnaire method
        print("\n4️⃣ Testing questionnaire entity retrieval...")
        entities = await zep_service.get_questionnaire_entities(test_user_id)
        print(f"📊 Questionnaire entities: {len(entities)}")
        
        if entities:
            print("✅ Questionnaire retrieval working")
        else:
            print("⚠️  No questionnaire entities found (expected for test data)")
        
        # Step 5: Test our add_or_update method
        print("\n5️⃣ Testing add_or_update_business_context...")
        entity_data = {
            "entity_id": "business_profile_q1",
            "entity_type": "business_profile_question", 
            "question": "Test question",
            "answer": "Test answer",
            "question_number": 1,
            "category": "test"
        }
        
        await zep_service.add_or_update_business_context(test_user_id, entity_data)
        print("✅ add_or_update_business_context completed")
        
        # Wait and check again
        await asyncio.sleep(3)
        
        # Step 6: Check memory session directly
        print("\n6️⃣ Checking memory session...")
        session_id = f"business_profile_{test_user_id}"
        try:
            memory = zep_service.client.memory.get(session_id=session_id)
            print(f"✅ Memory session exists")
            
            if hasattr(memory, "messages") and memory.messages:
                print(f"📊 Found {len(memory.messages)} messages in session")
                for i, msg in enumerate(memory.messages):
                    content = getattr(msg, 'content', 'No content')
                    print(f"   Message {i+1}: {content[:100]}...")
            else:
                print("⚠️  No messages in memory session")
                
        except Exception as e:
            print(f"❌ Error accessing memory session: {e}")
        
        # Step 7: Test questionnaire entities retrieval with debugging
        print("\n7️⃣ Debugging questionnaire entity parsing...")
        
        # Let's manually test the parsing logic
        test_content = "Business Profile Context: Q1 (test): Test question\nAnswer: Test answer"
        print(f"Test content: {test_content}")
        
        lines = test_content.split('\n')
        current_entity = {}
        
        for line in lines:
            line = line.strip()
            print(f"Processing line: '{line}'")
            
            if line.startswith('Q') and '(' in line and ')' in line:
                print("  → Matched question line")
                try:
                    q_part, rest = line.split(':', 1)
                    q_num_part = q_part.split('(')[0].strip()
                    category_part = q_part.split('(')[1].split(')')[0].strip()
                    question_num = int(q_num_part[1:])  # Remove 'Q' prefix
                    
                    current_entity = {
                        'entity_id': f'business_profile_q{question_num}',
                        'question_number': question_num,
                        'question': rest.strip(),
                        'category': category_part
                    }
                    print(f"  → Created entity: {current_entity}")
                except (ValueError, IndexError) as e:
                    print(f"  → Error parsing: {e}")
                    
            elif line.startswith('Answer:') and current_entity:
                print("  → Matched answer line")
                answer = line[7:].strip()  # Remove "Answer:" prefix
                current_entity['answer'] = answer
                print(f"  → Final entity: {current_entity}")
        
        # Now test the actual method
        questionnaire_entities = await zep_service.get_questionnaire_entities(test_user_id)
        print(f"📊 Questionnaire entities after add: {len(questionnaire_entities)}")
        
        if questionnaire_entities:
            print("✅ SUCCESS: Questionnaire entity creation working")
            for entity in questionnaire_entities:
                print(f"   Entity: {entity.get('entity_id')} - {entity.get('answer', 'No answer')}")
        else:
            print("❌ No questionnaire entities found")
        
    except Exception as e:
        print(f"❌ Error during debug: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        try:
            zep_service.manager.delete_user_data(test_user_id)
            print("✅ Cleaned up test user")
        except Exception as e:
            print(f"⚠️  Cleanup error: {e}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(debug_zep_graph())