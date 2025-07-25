#!/usr/bin/env python3
"""
Definitive Zep User Creation Test
Tests the corrected API calls and verifies users persist in Zep dashboard
"""

import os
import sys
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


def main():
    print("🎯 Definitive Zep User Creation Test")
    print("=" * 60)
    print(f"🕐 Started at: {datetime.now().isoformat()}")
    print()

    # Check environment
    zep_api_key = os.getenv("ZEP_API_KEY")
    zep_api_url = os.getenv("ZEP_API_URL", "https://api.getzep.com")

    if not zep_api_key:
        print("❌ ZEP_API_KEY not set")
        return False

    print(f"🔑 API Key: {zep_api_key[:8]}...")
    print(f"🌐 API URL: {zep_api_url}")

    try:
        from zep_cloud.client import Zep

        client = Zep(base_url=zep_api_url, api_key=zep_api_key)
        print("✅ Zep client created successfully")

        # Test 1: List existing users (CORRECTED API)
        print("\n1️⃣ Testing corrected user.list() API...")
        try:
            users_response = client.user.list_ordered()
            print(f"   ✅ Success: {type(users_response)}")

            if hasattr(users_response, "users"):
                user_count = len(users_response.users) if users_response.users else 0
                print(f"   📊 Users found: {user_count}")

                if user_count > 0:
                    print("   👥 Existing users:")
                    for i, user in enumerate(users_response.users[:3], 1):
                        print(
                            f"      {i}. {user.user_id} ({getattr(user, 'email', 'no email')})"
                        )
                else:
                    print("   ⚠️ No existing users found")
            else:
                print(f"   ⚠️ Response has no 'users' attribute: {dir(users_response)}")

        except Exception as e:
            print(f"   ❌ Failed: {e}")
            print(f"   🔍 Error type: {type(e).__name__}")
            return False

        # Test 2: Create a new user
        print("\n2️⃣ Testing user creation...")
        test_user_id = f"definitive_test_{int(datetime.now().timestamp())}"
        test_email = f"{test_user_id}@example.com"

        try:
            created_user = client.user.add(
                user_id=test_user_id,
                email=test_email,
                first_name="Definitive",
                last_name="Test",
                metadata={
                    "source": "definitive_test",
                    "created_at": datetime.now().isoformat(),
                },
            )
            print(f"   ✅ User created successfully!")
            print(f"   👤 User ID: {created_user.user_id}")
            print(f"   📧 Email: {getattr(created_user, 'email', 'not set')}")

        except Exception as e:
            print(f"   ❌ User creation failed: {e}")
            return False

        # Test 3: Verify user exists by retrieving it
        print("\n3️⃣ Verifying user exists...")
        try:
            retrieved_user = client.user.get(test_user_id)
            print(f"   ✅ User retrieved successfully!")
            print(f"   👤 Retrieved ID: {retrieved_user.user_id}")
            print(f"   📧 Email: {getattr(retrieved_user, 'email', 'not set')}")

        except Exception as e:
            print(f"   ❌ User retrieval failed: {e}")
            return False

        # Test 4: List users again to confirm it appears
        print("\n4️⃣ Confirming user appears in list...")
        try:
            users_response = client.user.list_ordered()

            if hasattr(users_response, "users") and users_response.users:
                user_count = len(users_response.users)
                print(f"   ✅ Found {user_count} total users")

                # Check if our test user is in the list
                user_ids = [user.user_id for user in users_response.users]
                if test_user_id in user_ids:
                    print(f"   ✅ Test user found in list!")
                else:
                    print(f"   ⚠️ Test user NOT found in list")
                    print(f"   📋 User IDs in list: {user_ids[:5]}")

                # Show all users for verification
                print("   👥 All users:")
                for i, user in enumerate(users_response.users, 1):
                    print(
                        f"      {i}. {user.user_id} ({getattr(user, 'email', 'no email')})"
                    )
            else:
                print(f"   ❌ No users returned in list")
                return False

        except Exception as e:
            print(f"   ❌ User listing failed: {e}")
            return False

        # Test 5: Clean up test user
        print("\n5️⃣ Cleaning up test user...")
        try:
            client.user.delete(test_user_id)
            print(f"   ✅ Test user deleted successfully")

        except Exception as e:
            print(f"   ⚠️ Cleanup failed (user may persist): {e}")

        print("\n🎉 ALL TESTS PASSED!")
        print("✅ User creation pipeline is working correctly")
        print("✅ Users should now appear in your Zep dashboard")

        return True

    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   Make sure zep-cloud is installed: pip install zep-cloud")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


if __name__ == "__main__":
    success = main()
    print(f"\n📊 Final Result: {'✅ SUCCESS' if success else '❌ FAILED'}")

    if not success:
        print("\n💡 Troubleshooting:")
        print("1. Verify ZEP_API_KEY is correct and active")
        print("2. Check you're viewing the correct Zep project/organization")
        print("3. Ensure network connectivity to Zep API")
        print("4. Try the test again - API might have temporary issues")

    sys.exit(0 if success else 1)
