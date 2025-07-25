#!/usr/bin/env python3
"""
Production Zep Debug Script
Comprehensive debugging for production Zep user creation issues
"""

import os
import sys
import logging
import json
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_environment_variables():
    """Test all required environment variables"""
    print("🔧 Environment Variables Check")
    print("=" * 50)

    required_vars = {
        "ZEP_API_KEY": os.getenv("ZEP_API_KEY"),
        "ZEP_API_URL": os.getenv("ZEP_API_URL", "https://api.getzep.com"),
        "NEO4J_URI": os.getenv("NEO4J_URI"),
        "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY"),
    }

    all_good = True
    for var_name, var_value in required_vars.items():
        if var_value:
            # Mask sensitive values
            if "KEY" in var_name:
                display_value = f"{var_value[:8]}..." if len(var_value) > 8 else "***"
            else:
                display_value = var_value
            print(f"✅ {var_name}: {display_value}")
        else:
            print(f"❌ {var_name}: NOT SET")
            all_good = False

    print(f"\nEnvironment Status: {'✅ PASS' if all_good else '❌ FAIL'}")
    return all_good


def test_zep_connectivity():
    """Test basic Zep API connectivity"""
    print("\n🌐 Zep API Connectivity Test")
    print("=" * 50)

    zep_api_key = os.getenv("ZEP_API_KEY")
    zep_api_url = os.getenv("ZEP_API_URL", "https://api.getzep.com")

    if not zep_api_key:
        print("❌ ZEP_API_KEY not set")
        return False

    try:
        from zep_cloud.client import Zep

        print(f"📡 Connecting to: {zep_api_url}")
        print(f"🔑 Using API key: {zep_api_key[:8]}...")

        client = Zep(base_url=zep_api_url, api_key=zep_api_key)

        # Try to list users (minimal operation)
        print("🔍 Testing user.list_ordered endpoint...")
        users_response = client.user.list_ordered()
        print(f"✅ API connectivity successful")
        print(f"📊 Response type: {type(users_response)}")

        # Check if users exist
        if hasattr(users_response, "users") and users_response.users:
            print(f"👥 Found {len(users_response.users)} existing users")
            for user in users_response.users[:3]:  # Show first 3
                print(f"   - User ID: {user.user_id}")
        else:
            print("👥 No existing users found (this might be the issue)")

        return True

    except Exception as e:
        print(f"❌ Zep connectivity failed: {e}")
        print(f"🔍 Error type: {type(e).__name__}")

        # Check for common errors
        if "401" in str(e) or "Unauthorized" in str(e):
            print("🚨 Authentication error - check your API key")
        elif "403" in str(e) or "Forbidden" in str(e):
            print("🚨 Authorization error - check API key permissions")
        elif "404" in str(e) or "Not Found" in str(e):
            print("🚨 URL error - check ZEP_API_URL")
        elif "timeout" in str(e).lower():
            print("🚨 Timeout error - check network connectivity")

        return False


def test_user_creation_flow():
    """Test the complete user creation flow"""
    print("\n👤 User Creation Flow Test")
    print("=" * 50)

    try:
        from zep_memory import zep_memory

        if not zep_memory.enabled:
            print("❌ Zep memory manager is disabled")
            return False

        # Test user creation with comprehensive metadata
        test_user_id = f"test_user_debug_{int(datetime.now().timestamp())}"
        test_metadata = {
            "email": f"test_{test_user_id}@example.com",
            "first_name": "Debug",
            "last_name": "User",
            "user_type": "business_owner",
            "source": "debug_script",
            "created_at": datetime.now().isoformat(),
        }

        print(f"🧪 Creating test user: {test_user_id}")
        print(f"📋 Metadata: {json.dumps(test_metadata, indent=2)}")

        # Test user creation
        user = zep_memory.ensure_user_exists(test_user_id, test_metadata)

        if user:
            print(f"✅ User creation successful!")
            print(f"👤 User ID: {user.user_id}")
            print(f"📧 Email: {getattr(user, 'email', 'Not set')}")
            print(f"📝 Metadata: {getattr(user, 'metadata', {})}")

            # Test user retrieval
            print("\n🔍 Testing user retrieval...")
            retrieved_user = zep_memory._get_user_with_circuit_breaker(test_user_id)
            print(f"✅ User retrieval successful: {retrieved_user.user_id}")

            # Clean up test user
            print("\n🧹 Cleaning up test user...")
            cleanup_success = zep_memory.delete_user_data(test_user_id)
            print(
                f"{'✅' if cleanup_success else '⚠️'} Cleanup {'successful' if cleanup_success else 'failed'}"
            )

            return True
        else:
            print("❌ User creation returned None")
            return False

    except Exception as e:
        print(f"❌ User creation failed: {e}")
        print(f"🔍 Error type: {type(e).__name__}")

        # Check for circuit breaker issues
        if "CircuitBreakerOpenError" in str(e):
            print("🚨 Circuit breaker is open - API calls are being blocked")
            print("   This suggests previous failures. Wait 30 seconds and try again.")

        return False


def test_existing_users():
    """Check for existing users in the system"""
    print("\n👥 Existing Users Analysis")
    print("=" * 50)

    try:
        from zep_cloud.client import Zep

        zep_api_key = os.getenv("ZEP_API_KEY")
        zep_api_url = os.getenv("ZEP_API_URL", "https://api.getzep.com")

        client = Zep(base_url=zep_api_url, api_key=zep_api_key)

        # Get user list with more details
        print("🔍 Fetching existing users...")
        users_response = client.user.list_ordered()

        if hasattr(users_response, "users") and users_response.users:
            print(f"✅ Found {len(users_response.users)} users:")

            for i, user in enumerate(users_response.users, 1):
                print(f"\n  👤 User #{i}:")
                print(f"     ID: {user.user_id}")
                print(f"     Email: {getattr(user, 'email', 'Not set')}")
                print(f"     First Name: {getattr(user, 'first_name', 'Not set')}")
                print(f"     Last Name: {getattr(user, 'last_name', 'Not set')}")
                print(f"     Created: {getattr(user, 'created_at', 'Unknown')}")
                print(f"     Metadata: {getattr(user, 'metadata', {})}")

                # Check for sessions
                try:
                    # Note: Zep might not have a direct way to list sessions for a user
                    # This is informational only
                    print(f"     Sessions: [Session listing not directly available]")
                except Exception:
                    pass
        else:
            print("❌ No users found in Zep")
            print("🔍 This confirms the issue - users are not being created")

        return True

    except Exception as e:
        print(f"❌ Failed to analyze existing users: {e}")
        return False


def test_circuit_breakers():
    """Test circuit breaker status"""
    print("\n⚡ Circuit Breaker Status")
    print("=" * 50)

    try:
        from circuit_breaker import circuit_breaker_decorator

        # Check if circuit breakers exist and their states
        if hasattr(circuit_breaker_decorator, "_breakers"):
            breakers = circuit_breaker_decorator._breakers

            if breakers:
                for name, breaker in breakers.items():
                    print(f"🔧 {name}:")
                    print(f"   State: {breaker.state}")
                    print(f"   Failure Count: {breaker.failure_count}")
                    print(f"   Last Failure: {breaker.last_failure_time}")
                    print(f"   Threshold: {breaker.failure_threshold}")
                    print()
            else:
                print("ℹ️ No circuit breakers currently active")
        else:
            print("⚠️ Circuit breaker decorator not properly initialized")

        return True

    except Exception as e:
        print(f"❌ Failed to check circuit breakers: {e}")
        return False


def main():
    """Run complete production debugging suite"""
    print("🎯 Zep Production Debug Suite")
    print("=" * 70)
    print(f"🕐 Started at: {datetime.now().isoformat()}")
    print()

    results = {
        "environment": test_environment_variables(),
        "connectivity": False,
        "user_creation": False,
        "existing_users": False,
        "circuit_breakers": False,
    }

    # Only proceed with other tests if environment is good
    if results["environment"]:
        results["connectivity"] = test_zep_connectivity()

        if results["connectivity"]:
            results["existing_users"] = test_existing_users()
            results["user_creation"] = test_user_creation_flow()

        results["circuit_breakers"] = test_circuit_breakers()

    # Summary
    print("\n📊 Debug Summary")
    print("=" * 50)
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name.replace('_', ' ').title()}: {status}")

    overall_status = all(results.values())
    print(
        f"\nOverall Status: {'✅ ALL TESTS PASSED' if overall_status else '❌ ISSUES FOUND'}"
    )

    if not overall_status:
        print("\n🔧 Recommended Actions:")
        if not results["environment"]:
            print("1. Fix environment variable configuration")
        if not results["connectivity"]:
            print("2. Check API key and network connectivity")
        if not results["user_creation"]:
            print("3. Debug user creation flow")
        if not results["existing_users"]:
            print("4. Investigate why no users exist in Zep")
        if not results["circuit_breakers"]:
            print("5. Check circuit breaker configuration")

    return overall_status


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
