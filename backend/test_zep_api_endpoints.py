#!/usr/bin/env python3
"""
Test specific Zep API endpoints to identify version mismatches
"""

import os
import sys
from datetime import datetime

def test_api_endpoints():
    """Test different API endpoint variations"""
    print("🔍 Testing Zep API Endpoint Variations")
    print("=" * 50)
    
    # Load environment variables
    env_vars = {}
    try:
        with open('.env', 'r') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    env_vars[key] = value
    except FileNotFoundError:
        print("❌ .env file not found")
        return False
    
    zep_api_key = os.getenv("ZEP_API_KEY") or env_vars.get("ZEP_API_KEY")
    zep_api_url = os.getenv("ZEP_API_URL") or env_vars.get("ZEP_API_URL", "https://api.getzep.com")
    
    if not zep_api_key:
        print("❌ ZEP_API_KEY not found")
        return False
    
    print(f"🔑 API Key: {zep_api_key[:8]}...")
    print(f"🌐 API URL: {zep_api_url}")
    
    try:
        from zep_cloud.client import Zep
        client = Zep(base_url=zep_api_url, api_key=zep_api_key)
        print("✅ Zep client created successfully")
        
        # Test 1: user.list_ordered (the failing method)
        print("\n1️⃣ Testing user.list_ordered()...")
        try:
            result = client.user.list_ordered(page_size=1)
            print(f"   ✅ Success: {type(result)}")
            if hasattr(result, 'users'):
                print(f"   📊 Users found: {len(result.users) if result.users else 0}")
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            print(f"   🔍 Error type: {type(e).__name__}")
        
        # Test 2: Alternative user.list method  
        print("\n2️⃣ Testing user.list()...")
        try:
            result = client.user.list(limit=1)
            print(f"   ✅ Success: {type(result)}")
            if hasattr(result, 'users'):
                print(f"   📊 Users found: {len(result.users) if result.users else 0}")
        except Exception as e:
            print(f"   ❌ Failed: {e}")
        
        # Test 3: Create a simple user
        print("\n3️⃣ Testing user.add()...")
        test_user_id = f"endpoint_test_{int(datetime.now().timestamp())}"
        try:
            user = client.user.add(
                user_id=test_user_id,
                email=f"{test_user_id}@test.com",
                metadata={"test": True}
            )
            print(f"   ✅ User created: {user.user_id}")
            
            # Test 4: Get the user back
            print("\n4️⃣ Testing user.get()...")
            retrieved = client.user.get(test_user_id)
            print(f"   ✅ User retrieved: {retrieved.user_id}")
            
            # Test 5: Delete the user
            print("\n5️⃣ Testing user.delete()...")
            client.user.delete(test_user_id)
            print(f"   ✅ User deleted: {test_user_id}")
            
        except Exception as e:
            print(f"   ❌ User operations failed: {e}")
            print(f"   🔍 Error details: {type(e).__name__}")
            
            # Try to understand the error better
            error_str = str(e).lower()
            if "404" in error_str:
                print("   🚨 404 Error - API endpoint doesn't exist")
                print("   💡 This suggests API version mismatch")
            elif "401" in error_str or "unauthorized" in error_str:
                print("   🚨 401 Error - Authentication failed")
            elif "403" in error_str:
                print("   🚨 403 Error - Permission denied")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Client creation failed: {e}")
        return False

def check_package_versions():
    """Check installed Zep package versions"""
    print("\n📦 Checking Package Versions")
    print("=" * 30)
    
    try:
        import zep_cloud
        print(f"✅ zep-cloud version: {zep_cloud.__version__}")
    except ImportError:
        print("❌ zep-cloud not installed")
    except AttributeError:
        print("⚠️ zep-cloud installed but no version info")
    
    try:
        import zep_python
        print(f"⚠️ zep-python also installed: {zep_python.__version__}")
        print("   💡 Having both packages may cause conflicts")
    except ImportError:
        print("✅ zep-python not installed (good)")
    except AttributeError:
        print("⚠️ zep-python installed but no version info")

def main():
    """Run endpoint testing"""
    print("🎯 Zep API Endpoint Testing")
    print("=" * 60)
    print(f"🕐 Started at: {datetime.now().isoformat()}")
    
    check_package_versions()
    success = test_api_endpoints()
    
    print(f"\n📊 Test Result: {'✅ SUCCESS' if success else '❌ FAILED'}")
    
    if not success:
        print("\n💡 Recommendations:")
        print("1. Check if API endpoints have changed in latest Zep version")
        print("2. Review Zep documentation for correct API usage")
        print("3. Consider updating to latest zep-cloud package")
        print("4. Remove conflicting zep-python package if present")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)