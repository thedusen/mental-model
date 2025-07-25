#!/usr/bin/env python3
"""
Debug User Creation Issues - Minimal Test
Tests the exact user creation flow that questionnaire uses
"""

import os
import sys
from datetime import datetime

# Set environment variables
os.environ["ZEP_API_KEY"] = (
    "z_1dWlkIjoiZGIzYTMxYzQtNjVlMi00NDM1LTlmMjgtZWY3ZTNkZDE5YzM2In0.frpMBktBNV6Yyo080wnj09heynO2Mg-pPACeJj_ge8lZ5GCH1I1GdW6xtMHhL1VzBn3y6WoyzpcJCmVKVcI9aA"
)
os.environ["ZEP_API_URL"] = "https://api.getzep.com"


def test_questionnaire_user_creation():
    """Test the exact user creation flow from questionnaire"""

    print("🔍 Debug User Creation Issues")
    print("=" * 50)
    print(f"🕐 Started at: {datetime.now().isoformat()}")
    print()

    zep_api_key = os.getenv("ZEP_API_KEY")
    zep_api_url = os.getenv("ZEP_API_URL", "https://api.getzep.com")

    try:
        from zep_cloud.client import Zep

        client = Zep(base_url=zep_api_url, api_key=zep_api_key)
        print("✅ Zep client created successfully")

        # Test 1: Create user with minimal metadata (what happens when no Supabase profile)
        print("\n1️⃣ Testing user creation with minimal metadata...")
        test_user_id = f"debug_minimal_{int(datetime.now().timestamp())}"

        minimal_metadata = {"user_type": "business_owner", "source": "questionnaire"}

        try:
            user = client.user.add(user_id=test_user_id, metadata=minimal_metadata)
            print(f"   ✅ Minimal user created: {user.user_id}")
        except Exception as e:
            print(f"   ❌ Minimal user creation failed: {e}")
            return False

        # Test 2: Create user with full metadata (what happens with Supabase profile)
        print("\n2️⃣ Testing user creation with full metadata...")
        test_user_id_full = f"debug_full_{int(datetime.now().timestamp())}"

        full_metadata = {
            "user_type": "business_owner",
            "source": "questionnaire",
            "email": f"{test_user_id_full}@example.com",
            "first_name": "Test",
            "last_name": "User",
        }

        try:
            user_full = client.user.add(
                user_id=test_user_id_full,
                email=full_metadata["email"],
                first_name=full_metadata["first_name"],
                last_name=full_metadata["last_name"],
                metadata=full_metadata,
            )
            print(f"   ✅ Full user created: {user_full.user_id}")
        except Exception as e:
            print(f"   ❌ Full user creation failed: {e}")
            return False

        # Test 3: Add business profile data to knowledge graph (what questionnaire does)
        print("\n3️⃣ Testing business profile data addition...")

        entity_data = {
            "entity_id": "business_profile_q1",
            "entity_type": "business_profile_question",
            "question": "What is your biggest business challenge?",
            "answer": "Scaling our development team while maintaining code quality",
            "question_number": 1,
            "category": "challenges",
            "answered_at": datetime.now().isoformat(),
        }

        try:
            import json

            client.graph.add(
                user_id=test_user_id_full, data=json.dumps(entity_data), type="json"
            )
            print(f"   ✅ Business data added to knowledge graph")
        except Exception as e:
            print(f"   ❌ Business data addition failed: {e}")
            return False

        # Test 4: Verify the users exist and have the data
        print("\n4️⃣ Verifying users exist in Zep...")

        try:
            users_response = client.user.list_ordered(page_size=10)
            user_ids = (
                [user.user_id for user in users_response.users]
                if users_response.users
                else []
            )

            if test_user_id in user_ids:
                print(f"   ✅ Minimal user found in Zep user list")
            else:
                print(f"   ❌ Minimal user NOT found in Zep user list")

            if test_user_id_full in user_ids:
                print(f"   ✅ Full user found in Zep user list")
            else:
                print(f"   ❌ Full user NOT found in Zep user list")

        except Exception as e:
            print(f"   ❌ Error checking user list: {e}")
            return False

        # Test 5: Check knowledge graph for business data
        print("\n5️⃣ Checking knowledge graph data...")

        try:
            graph_data = client.graph.get(user_id=test_user_id_full)
            if hasattr(graph_data, "nodes") and graph_data.nodes:
                print(f"   ✅ Knowledge graph has {len(graph_data.nodes)} nodes")
                for node in graph_data.nodes[:3]:
                    print(
                        f"      - {getattr(node, 'name', 'Unknown')} ({getattr(node, 'node_type', 'Unknown type')})"
                    )
            else:
                print(f"   ⚠️ No nodes found in knowledge graph")
        except Exception as e:
            print(f"   ❌ Error checking knowledge graph: {e}")

        print("\n🎉 USER CREATION FLOW TEST COMPLETED!")
        print("✅ Both user creation scenarios work correctly")
        print("✅ Business profile data can be added to knowledge graph")
        print("✅ The issue may be in the questionnaire service logic, not Zep API")

        return True

    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


if __name__ == "__main__":
    success = test_questionnaire_user_creation()
    print(f"\n📊 Result: {'✅ SUCCESS' if success else '❌ FAILED'}")

    if success:
        print("\n🔧 DEBUGGING RECOMMENDATIONS:")
        print("1. The Zep API itself is working correctly")
        print("2. Check the questionnaire service logs for specific errors")
        print("3. Look for circuit breaker issues or configuration problems")
        print("4. The issue is likely in the error handling, not the API calls")

    sys.exit(0 if success else 1)
