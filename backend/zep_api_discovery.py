#!/usr/bin/env python3
"""
Zep API Discovery
Find out what methods are actually available on the UserClient
"""

import os
from datetime import datetime

# Set environment variables
os.environ['ZEP_API_KEY'] = 'z_1dWlkIjoiZGIzYTMxYzQtNjVlMi00NDM1LTlmMjgtZWY3ZTNkZDE5YzM2In0.frpMBktBNV6Yyo080wnj09heynO2Mg-pPACeJj_ge8lZ5GCH1I1GdW6xtMHhL1VzBn3y6WoyzpcJCmVKVcI9aA'
os.environ['ZEP_API_URL'] = 'https://api.getzep.com'

def main():
    print("🔍 Zep API Discovery")
    print("=" * 40)
    print(f"🕐 Started at: {datetime.now().isoformat()}")
    print()

    try:
        from zep_cloud.client import Zep

        zep_api_key = os.getenv("ZEP_API_KEY")
        zep_api_url = os.getenv("ZEP_API_URL")
        
        client = Zep(base_url=zep_api_url, api_key=zep_api_key)
        print("✅ Zep client created successfully")

        # Inspect the user client
        print(f"\n📋 UserClient type: {type(client.user)}")
        print(f"📋 Available methods on UserClient:")
        
        user_methods = [method for method in dir(client.user) if not method.startswith('_')]
        for method in sorted(user_methods):
            print(f"   - {method}")

        # Test the methods we found working before
        print(f"\n🧪 Testing known working methods:")
        
        # Try add method (this should work)
        print(f"\n1️⃣ Testing user.add()...")
        try:
            test_user_id = f"api_discovery_{int(datetime.now().timestamp())}"
            user = client.user.add(
                user_id=test_user_id,
                email=f"{test_user_id}@example.com",
                first_name="API",
                last_name="Discovery"
            )
            print(f"   ✅ user.add() works!")
            print(f"   👤 Created user: {user.user_id if hasattr(user, 'user_id') else 'Unknown'}")
            created_user_id = test_user_id
        except Exception as e:
            print(f"   ❌ user.add() failed: {e}")
            created_user_id = None

        # Try different list methods
        list_methods = ['list', 'list_ordered', 'get_all', 'list_users', 'get_users']
        for method_name in list_methods:
            print(f"\n🔍 Testing user.{method_name}()...")
            try:
                if hasattr(client.user, method_name):
                    method = getattr(client.user, method_name)
                    # Try calling with no args first
                    try:
                        result = method()
                        print(f"   ✅ user.{method_name}() works! Result type: {type(result)}")
                        if hasattr(result, 'users'):
                            print(f"   📊 Users count: {len(result.users) if result.users else 0}")
                    except Exception as e:
                        # Try with limit parameter
                        try:
                            result = method(limit=5)
                            print(f"   ✅ user.{method_name}(limit=5) works! Result type: {type(result)}")
                            if hasattr(result, 'users'):
                                print(f"   📊 Users count: {len(result.users) if result.users else 0}")
                        except Exception as e2:
                            # Try with page_size parameter
                            try:
                                result = method(page_size=5)
                                print(f"   ✅ user.{method_name}(page_size=5) works! Result type: {type(result)}")
                                if hasattr(result, 'users'):
                                    print(f"   📊 Users count: {len(result.users) if result.users else 0}")
                            except Exception as e3:
                                print(f"   ❌ user.{method_name}() failed: {e}")
                else:
                    print(f"   ❌ user.{method_name} method does not exist")
            except Exception as outer_e:
                print(f"   ❌ Error testing user.{method_name}: {outer_e}")

        # Try to get our created user
        if created_user_id:
            print(f"\n🔍 Testing user.get() to retrieve created user...")
            try:
                retrieved_user = client.user.get(created_user_id)
                print(f"   ✅ user.get() works!")
                print(f"   👤 Retrieved: {retrieved_user.user_id if hasattr(retrieved_user, 'user_id') else 'Unknown'}")
            except Exception as e:
                print(f"   ❌ user.get() failed: {e}")

        print(f"\n🎯 API Discovery Complete!")
        
    except Exception as e:
        print(f"❌ Discovery failed: {e}")
        return False

if __name__ == "__main__":
    main()