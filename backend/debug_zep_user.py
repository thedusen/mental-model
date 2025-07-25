#!/usr/bin/env python3
"""
Debug Zep User Creation Issues
Check user metadata and knowledge graph completeness
"""

import os
import sys
import json
from datetime import datetime

def debug_zep_user(user_id: str):
    """Debug specific Zep user and their data"""
    print(f"🔍 DEBUGGING ZEP USER: {user_id}")
    print("=" * 60)
    print(f"🕐 Started at: {datetime.now().isoformat()}")
    print()

    try:
        from zep_cloud.client import Zep
        
        # Initialize Zep client
        zep_api_key = os.getenv("ZEP_API_KEY")
        zep_api_url = os.getenv("ZEP_API_URL", "https://api.getzep.com")
        
        if not zep_api_key:
            print("❌ ZEP_API_KEY not found in environment")
            return False
            
        client = Zep(base_url=zep_api_url, api_key=zep_api_key)
        
        # 1. Get user details
        print("1️⃣ USER DETAILS")
        print("-" * 30)
        
        try:
            user = client.user.get(user_id)
            print(f"✅ User found: {user.user_id}")
            print(f"   Email: {getattr(user, 'email', 'Not set')}")
            print(f"   First Name: {getattr(user, 'first_name', 'Not set')}")
            print(f"   Last Name: {getattr(user, 'last_name', 'Not set')}")
            print(f"   Metadata: {getattr(user, 'metadata', {})}")
            print(f"   Created: {getattr(user, 'created_at', 'Unknown')}")
        except Exception as e:
            print(f"❌ Failed to get user: {e}")
            return False
            
        # 2. Get user's sessions
        print("\n2️⃣ USER SESSIONS")
        print("-" * 30)
        
        try:
            sessions = client.memory.get_sessions(user_id=user_id)
            if hasattr(sessions, 'sessions') and sessions.sessions:
                print(f"✅ Found {len(sessions.sessions)} sessions")
                for session in sessions.sessions[:3]:  # Show first 3
                    print(f"   Session: {session.session_id}")
                    print(f"   Created: {getattr(session, 'created_at', 'Unknown')}")
            else:
                print("⚠️ No sessions found")
        except Exception as e:
            print(f"❌ Failed to get sessions: {e}")
            
        # 3. Get user's knowledge graph entities  
        print("\n3️⃣ KNOWLEDGE GRAPH ENTITIES")
        print("-" * 30)
        
        try:
            # Try to get user's knowledge graph
            entities = client.graph.get_entities(user_id=user_id)
            if hasattr(entities, 'entities') and entities.entities:
                print(f"✅ Found {len(entities.entities)} entities")
                business_profile_entities = []
                
                for entity in entities.entities:
                    if hasattr(entity, 'entity_type') and 'business_profile' in str(entity.entity_type).lower():
                        business_profile_entities.append(entity)
                        
                print(f"   Business profile entities: {len(business_profile_entities)}")
                
                # Show details of business profile entities
                if business_profile_entities:
                    print("\n   📋 Business Profile Questions Found:")
                    for entity in sorted(business_profile_entities, key=lambda x: getattr(x, 'entity_id', '')):
                        entity_id = getattr(entity, 'entity_id', 'Unknown')
                        entity_type = getattr(entity, 'entity_type', 'Unknown')
                        
                        # Try to get entity data
                        if hasattr(entity, 'data'):
                            data = entity.data
                            question_num = data.get('question_number', 'Unknown')
                            question_text = data.get('question', 'No question text')[:50] + "..."
                            answer = data.get('answer', 'No answer')[:50] + "..."
                            print(f"      Q{question_num}: {question_text}")
                            print(f"         Answer: {answer}")
                        else:
                            print(f"      {entity_id}: {entity_type}")
                else:
                    print("   ⚠️ No business profile entities found")
                    
            else:
                print("⚠️ No entities found in knowledge graph")
                
        except Exception as e:
            print(f"❌ Failed to get knowledge graph: {e}")
            
        # 4. Check memory context
        print("\n4️⃣ MEMORY CONTEXT")
        print("-" * 30)
        
        try:
            # Get memory for the user
            memory = client.memory.get(user_id=user_id, limit=50)
            if hasattr(memory, 'messages') and memory.messages:
                print(f"✅ Found {len(memory.messages)} memory messages")
                questionnaire_messages = [m for m in memory.messages if 'questionnaire' in str(m).lower() or 'business' in str(m).lower()]
                print(f"   Questionnaire-related messages: {len(questionnaire_messages)}")
            else:
                print("⚠️ No memory messages found")
        except Exception as e:
            print(f"❌ Failed to get memory: {e}")
            
        return True
        
    except Exception as e:
        print(f"💥 CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_supabase_user_profile():
    """Check what user profile data exists in Supabase"""
    print("\n5️⃣ SUPABASE USER PROFILE CHECK")
    print("-" * 30)
    
    try:
        from supabase_client import SupabaseService
        supabase = SupabaseService()
        
        # Look for user profiles (we don't know the exact user_id, so get recent ones)
        response = supabase.client.table("user_profiles").select("*").limit(5).execute()
        
        if response.data:
            print(f"✅ Found {len(response.data)} user profiles in Supabase")
            for profile in response.data:
                print(f"   User ID: {profile.get('user_id', 'Unknown')}")
                print(f"   Email: {profile.get('email', 'Not set')}")
                print(f"   Name: {profile.get('first_name', '')} {profile.get('last_name', '')}")
                print(f"   Created: {profile.get('created_at', 'Unknown')}")
                print()
        else:
            print("⚠️ No user profiles found in Supabase")
            
    except Exception as e:
        print(f"❌ Failed to check Supabase profiles: {e}")

def check_questionnaire_responses():
    """Check questionnaire responses in Supabase"""
    print("\n6️⃣ QUESTIONNAIRE RESPONSES CHECK")
    print("-" * 30)
    
    try:
        from supabase_client import SupabaseService
        supabase = SupabaseService()
        
        # Get recent questionnaire responses
        response = supabase.client.table("user_questionnaire_responses").select("*, questionnaire_questions(question_text, question_number)").limit(20).execute()
        
        if response.data:
            print(f"✅ Found {len(response.data)} questionnaire responses")
            
            # Group by user
            users = {}
            for resp in response.data:
                user_id = resp.get('user_id')
                if user_id not in users:
                    users[user_id] = []
                users[user_id].append(resp)
                
            for user_id, responses in users.items():
                print(f"\n   User {user_id}: {len(responses)} responses")
                for resp in sorted(responses, key=lambda x: x.get('question_id', 0)):
                    q_num = resp.get('questionnaire_questions', {}).get('question_number', 'Unknown')
                    q_text = resp.get('questionnaire_questions', {}).get('question_text', 'Unknown')[:40] + "..."
                    answer = resp.get('response_text', 'No answer')[:40] + "..."
                    skipped = resp.get('skipped', False)
                    status = "SKIPPED" if skipped else "ANSWERED"
                    print(f"      Q{q_num}: {q_text} -> {answer} [{status}]")
        else:
            print("⚠️ No questionnaire responses found")
            
    except Exception as e:
        print(f"❌ Failed to check questionnaire responses: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python debug_zep_user.py <zep_user_id>")
        sys.exit(1)
        
    user_id = sys.argv[1]
    
    success = debug_zep_user(user_id)
    check_supabase_user_profile()
    check_questionnaire_responses()
    
    print(f"\n📊 DEBUG RESULT: {'✅ COMPLETED' if success else '❌ FAILED'}")