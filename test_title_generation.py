#!/usr/bin/env python3
"""
Test script to verify chat title generation functionality using API
"""

import requests
import json

def test_title_generation_via_api():
    """Test the title generation functionality using the backend API"""
    api_url = "http://localhost:8000"
    
    # Use an existing user from the database or create one
    # For now, let's use a known user ID that exists
    test_user_id = "fbe10dc0-6225-4f27-bee0-357025c365a9"  # This appears in the logs
    
    print("🧪 Testing title generation functionality via API...")
    print(f"Using test user ID: {test_user_id}")
    
    try:
        # 1. Create a chat session
        print("1. Creating chat session...")
        session_response = requests.post(f"{api_url}/api/chat/sessions", 
                                       json={"user_id": test_user_id})
        
        if session_response.status_code != 200:
            print(f"❌ Failed to create session: {session_response.status_code} - {session_response.text}")
            return
            
        session_data = session_response.json()
        session_id = session_data["id"]
        print(f"✅ Created session: {session_id}")
        
        # 2. Add a user message via API
        print("2. Adding user message via API...")
        user_message_response = requests.post(f"{api_url}/api/chat/messages",
                                            json={
                                                "session_id": session_id,
                                                "role": "user",
                                                "content": "What are the best strategies for customer segmentation in a B2B SaaS company?",
                                                "user_id": test_user_id,
                                                "metadata": {}
                                            })
        
        if user_message_response.status_code != 200:
            print(f"❌ Failed to add user message: {user_message_response.status_code} - {user_message_response.text}")
            return
            
        print(f"✅ Added user message: {user_message_response.json()}")
        
        # 3. Add an assistant message via API (this should trigger title generation)
        print("3. Adding assistant message via API (should trigger title generation)...")
        assistant_message_response = requests.post(f"{api_url}/api/chat/messages",
                                                 json={
                                                     "session_id": session_id,
                                                     "role": "assistant",
                                                     "content": "Great question! For B2B SaaS customer segmentation, I'd recommend focusing on these key strategies: 1) Firmographic segmentation (company size, industry, revenue), 2) Behavioral segmentation (usage patterns, feature adoption), 3) Needs-based segmentation (use cases, pain points), and 4) Value-based segmentation (customer lifetime value, growth potential). The key is to combine multiple dimensions to create actionable segments that align with your product offerings and go-to-market strategy.",
                                                     "user_id": test_user_id,
                                                     "metadata": {}
                                                 })
        
        if assistant_message_response.status_code != 200:
            print(f"❌ Failed to add assistant message: {assistant_message_response.status_code} - {assistant_message_response.text}")
            return
            
        print(f"✅ Added assistant message: {assistant_message_response.json()}")
        
        # 4. Check if session title was generated
        print("4. Checking if title was generated...")
        # Wait a moment for title generation to complete
        import time
        time.sleep(2)
        
        sessions_response = requests.get(f"{api_url}/api/chat/sessions/{test_user_id}")
        if sessions_response.status_code != 200:
            print(f"❌ Failed to get sessions: {sessions_response.status_code} - {sessions_response.text}")
            return
            
        sessions_data = sessions_response.json()
        target_session = None
        for session in sessions_data.get("sessions", []):
            if session["id"] == session_id:
                target_session = session
                break
                
        if target_session and target_session.get("title") and target_session["title"] != "Untitled conversation":
            print(f"🎉 SUCCESS! Title was generated: '{target_session['title']}'")
        else:
            print(f"❌ FAILURE! No title was generated. Session: {target_session}")
            
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_title_generation_via_api()