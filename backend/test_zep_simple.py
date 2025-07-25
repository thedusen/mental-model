#!/usr/bin/env python3
"""
Simple Zep Test - Direct API testing without external dependencies
"""

import os
import sys
import json
import requests
from datetime import datetime


def test_zep_api_direct():
    """Test Zep API directly using requests"""
    print("🧪 Direct Zep API Test")
    print("=" * 50)

    # Load environment variables from .env file manually
    env_vars = {}
    try:
        with open(".env", "r") as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    key, value = line.strip().split("=", 1)
                    env_vars[key] = value
    except FileNotFoundError:
        print("❌ .env file not found")
        return False

    zep_api_key = os.getenv("ZEP_API_KEY") or env_vars.get("ZEP_API_KEY")
    zep_api_url = os.getenv("ZEP_API_URL") or env_vars.get(
        "ZEP_API_URL", "https://api.getzep.com"
    )

    if not zep_api_key:
        print("❌ ZEP_API_KEY not found")
        return False

    print(f"🔑 API Key: {zep_api_key[:8]}...")
    print(f"🌐 API URL: {zep_api_url}")

    headers = {
        "Authorization": f"Bearer {zep_api_key}",
        "Content-Type": "application/json",
    }

    # Test 1: List users
    print("\n1️⃣ Testing user list endpoint...")
    try:
        response = requests.get(
            f"{zep_api_url}/api/v2/users-ordered?pageSize=5", headers=headers
        )
        print(f"   Status: {response.status_code}")

        if response.status_code == 200:
            users_data = response.json()
            print(f"   ✅ Success! Found data structure: {type(users_data)}")

            if "users" in users_data:
                users = users_data["users"]
                print(f"   👥 Total users: {len(users)}")

                if users:
                    print("   📋 Sample users:")
                    for i, user in enumerate(users[:3]):
                        print(f"      {i+1}. ID: {user.get('user_id', 'unknown')}")
                        print(f"         Email: {user.get('email', 'not set')}")
                        print(f"         Created: {user.get('created_at', 'unknown')}")
                else:
                    print("   ⚠️ No users found - this is likely the issue!")
            else:
                print(
                    f"   📊 Response structure: {json.dumps(users_data, indent=2)[:200]}..."
                )

        else:
            print(f"   ❌ Failed: {response.text}")
            return False

    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

    # Test 2: Create a test user
    print("\n2️⃣ Testing user creation...")
    test_user_id = f"debug_test_{int(datetime.now().timestamp())}"
    user_data = {
        "user_id": test_user_id,
        "email": f"{test_user_id}@example.com",
        "first_name": "Debug",
        "last_name": "Test",
        "metadata": {
            "source": "debug_script",
            "created_at": datetime.now().isoformat(),
        },
    }

    try:
        response = requests.post(
            f"{zep_api_url}/api/v2/users", headers=headers, json=user_data
        )
        print(f"   Status: {response.status_code}")

        if response.status_code in [200, 201]:
            created_user = response.json()
            print(f"   ✅ User created successfully!")
            print(f"   👤 User ID: {created_user.get('user_id', 'unknown')}")
            print(f"   📧 Email: {created_user.get('email', 'unknown')}")

            # Test 3: Retrieve the created user
            print("\n3️⃣ Testing user retrieval...")
            get_response = requests.get(
                f"{zep_api_url}/api/v2/users/{test_user_id}", headers=headers
            )
            print(f"   Status: {get_response.status_code}")

            if get_response.status_code == 200:
                retrieved_user = get_response.json()
                print(f"   ✅ User retrieved successfully!")
                print(f"   👤 Retrieved ID: {retrieved_user.get('user_id', 'unknown')}")
            else:
                print(f"   ❌ Retrieval failed: {get_response.text}")

            # Test 4: Clean up - delete the test user
            print("\n4️⃣ Cleaning up test user...")
            delete_response = requests.delete(
                f"{zep_api_url}/api/v2/users/{test_user_id}", headers=headers
            )
            print(f"   Cleanup status: {delete_response.status_code}")

            return True

        else:
            print(f"   ❌ User creation failed: {response.text}")

            # Check for common error patterns
            error_text = response.text.lower()
            if "unauthorized" in error_text or response.status_code == 401:
                print("   🚨 Authentication issue - check API key")
            elif "forbidden" in error_text or response.status_code == 403:
                print("   🚨 Permission issue - check API key permissions")
            elif "validation" in error_text or response.status_code == 422:
                print("   🚨 Validation error - check user data format")

            return False

    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


def main():
    """Run the test"""
    print("🎯 Simple Zep Production Test")
    print("=" * 60)
    print(f"🕐 Started at: {datetime.now().isoformat()}")
    print()

    success = test_zep_api_direct()

    print(f"\n📊 Final Result: {'✅ SUCCESS' if success else '❌ FAILED'}")

    if not success:
        print("\n💡 Troubleshooting Tips:")
        print("1. Verify ZEP_API_KEY is valid and active")
        print("2. Check if the API URL is correct")
        print("3. Ensure the API key has user creation permissions")
        print("4. Check for rate limiting or quota issues")
        print("5. Verify network connectivity to Zep API")

    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
