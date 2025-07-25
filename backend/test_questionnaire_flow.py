#!/usr/bin/env python3
"""
Test the complete questionnaire flow to debug user creation issues
"""

import os
import sys
import asyncio
from datetime import datetime

# Set environment variables for testing
os.environ['ZEP_API_KEY'] = 'z_1dWlkIjoiZGIzYTMxYzQtNjVlMi00NDM1LTlmMjgtZWY3ZTNkZTE5YzM2In0.frpMBktBNV6Yyo080wnj09heynO2Mg-pPACeJj_ge8lZ5GCH1I1GdW6xtMHhL1VzBn3y6WoyzpcJCmVKVcI9aA'
os.environ['ZEP_API_URL'] = 'https://api.getzep.com'

async def test_questionnaire_flow():
    """Test the complete questionnaire flow that users are experiencing"""
    
    print("🧪 Testing Complete Questionnaire Flow")
    print("=" * 60)
    print(f"🕐 Started at: {datetime.now().isoformat()}")
    print()
    
    try:
        # Import the questionnaire service
        from questionnaire_service import QuestionnaireService
        
        service = QuestionnaireService()
        print("✅ QuestionnaireService initialized successfully")
        
        # Test user ID
        test_user_id = f"questionnaire_test_{int(datetime.now().timestamp())}"
        print(f"👤 Test user ID: {test_user_id}")
        
        # Test 1: Start questionnaire
        print("\n1️⃣ Testing questionnaire start...")
        start_result = await service.start_questionnaire(test_user_id)
        print(f"   ✅ Start result: {start_result.get('message', 'No message')}")
        print(f"   📊 Progress: {start_result.get('progress')}")
        
        if not start_result.get('question'):
            print("   ❌ No question returned from start")
            return False
            
        first_question = start_result['question']
        print(f"   ❓ First question: {first_question.get('question_text', 'No text')}")
        
        # Test 2: Submit first answer (this should trigger user creation in Zep)
        print("\n2️⃣ Testing answer submission and Zep user creation...")
        test_answer = "My biggest challenge is scaling my development team while maintaining code quality"
        
        answer_result = await service.submit_answer(
            user_id=test_user_id,
            question_id=first_question['id'],
            answer_text=test_answer
        )
        
        print(f"   ✅ Answer submitted successfully")
        print(f"   📊 Progress after answer: {answer_result.get('progress')}")
        
        # Test 3: Check if user was created in Zep
        print("\n3️⃣ Checking if user was created in Zep...")
        
        from zep_cloud.client import Zep
        zep_client = Zep(
            base_url=os.getenv("ZEP_API_URL", "https://api.getzep.com"),
            api_key=os.getenv("ZEP_API_KEY")
        )
        
        try:
            zep_user = zep_client.user.get(test_user_id)
            print(f"   ✅ User found in Zep: {zep_user.user_id}")
            print(f"   📧 Email: {getattr(zep_user, 'email', 'None')}")
            print(f"   🏷️  Metadata: {getattr(zep_user, 'metadata', 'None')}")
            
            # Test 4: Check user's knowledge graph data
            print("\n4️⃣ Checking user's knowledge graph...")
            try:
                graph_data = zep_client.graph.get(user_id=test_user_id)
                if hasattr(graph_data, 'nodes') and graph_data.nodes:
                    print(f"   ✅ Knowledge graph has {len(graph_data.nodes)} nodes")
                    for i, node in enumerate(graph_data.nodes[:3], 1):
                        print(f"      {i}. {getattr(node, 'name', 'Unknown')} - {getattr(node, 'node_type', 'Unknown type')}")
                else:
                    print("   ⚠️ No nodes found in knowledge graph")
            except Exception as graph_error:
                print(f"   ❌ Error getting knowledge graph: {graph_error}")
            
        except Exception as user_error:
            print(f"   ❌ User NOT found in Zep: {user_error}")
            return False
        
        # Test 5: Submit one more answer to verify the flow
        print("\n5️⃣ Testing second answer submission...")
        second_answer = "We are a software consulting company with 15 employees"
        
        # First get the next question from the current state
        current_question = await service.get_current_question(test_user_id)
        if current_question and current_question.get('question'):
            next_question = current_question['question']
            
            second_answer_result = await service.submit_answer(
                user_id=test_user_id,
                question_id=next_question['id'],
                answer_text=second_answer
            )
            print(f"   ✅ Second answer submitted successfully")
            print(f"   📊 Progress: {second_answer_result.get('progress')}")
        else:
            print("   ❌ Could not get next question")
            
        print("\n🎉 QUESTIONNAIRE FLOW TEST COMPLETED!")
        print("✅ User creation in Zep is working through questionnaire flow")
        print("✅ Check your Zep dashboard to verify the user appears")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        print(f"🔍 Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_questionnaire_flow())
    print(f"\n📊 Final Result: {'✅ SUCCESS' if success else '❌ FAILED'}")
    sys.exit(0 if success else 1)