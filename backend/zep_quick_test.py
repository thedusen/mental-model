#!/usr/bin/env python3
"""
Quick Zep Test - Minimal dependencies
Tests the corrected API calls without dotenv
"""

import os
import sys
from datetime import datetime

# Set environment variables directly for testing
os.environ["ZEP_API_KEY"] = (
    "z_1dWlkIjoiZGIzYTMxYzQtNjVlMi00NDM1LTlmMjgtZWY3ZTNkZDE5YzM2In0.frpMBktBNV6Yyo080wnj09heynO2Mg-pPACeJj_ge8lZ5GCH1I1GdW6xtMHhL1VzBn3y6WoyzpcJCmVKVcI9aA"
)
os.environ["ZEP_API_URL"] = "https://api.getzep.com"


def main():
    print("🎯 Quick Zep User Creation Test")
    print("=" * 50)
    print(f"🕐 Started at: {datetime.now().isoformat()}")
    print()

    zep_api_key = os.getenv("ZEP_API_KEY")
    zep_api_url = os.getenv("ZEP_API_URL", "https://api.getzep.com")

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
                print(f"   ⚠️ Response structure: {dir(users_response)}")

        except Exception as e:
            print(f"   ❌ Failed: {e}")
            print(f"   🔍 Error type: {type(e).__name__}")
            return False

        # Test 2: Create a new user
        print("\n2️⃣ Testing user creation...")
        test_user_id = f"test_{int(datetime.now().timestamp())}"
        test_email = f"{test_user_id}@example.com"

        try:
            created_user = client.user.add(
                user_id=test_user_id,
                email=test_email,
                first_name="Test",
                last_name="User",
            )
            print(f"   ✅ User created successfully!")
            print(
                f"   👤 User ID: {created_user.user_id if hasattr(created_user, 'user_id') else 'Unknown'}"
            )

        except Exception as e:
            print(f"   ❌ User creation failed: {e}")
            return False

        # Test 3: List users again to see if it appears
        print("\n3️⃣ Listing users after creation...")
        try:
            users_response = client.user.list_ordered()

            if hasattr(users_response, "users") and users_response.users:
                user_count = len(users_response.users)
                print(f"   ✅ Found {user_count} total users")

                print("   👥 All users:")
                for i, user in enumerate(users_response.users, 1):
                    print(
                        f"      {i}. {user.user_id} ({getattr(user, 'email', 'no email')})"
                    )
            else:
                print(f"   ❌ No users returned")
                return False

        except Exception as e:
            print(f"   ❌ User listing failed: {e}")
            return False

        print("\n🎉 TEST COMPLETED!")
        print("✅ API calls are working with corrected methods")
        print("✅ Check your Zep dashboard to see if users appear")

        return True

    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   zep-cloud package may not be installed")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


if __name__ == "__main__":
    success = main()
    print(f"\n📊 Result: {'✅ SUCCESS' if success else '❌ FAILED'}")
    sys.exit(0 if success else 1)
