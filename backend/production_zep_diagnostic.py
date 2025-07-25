#!/usr/bin/env python3
"""
Production Zep Diagnostic Script
Comprehensive testing for production Zep integration issues
"""

import os
import sys
import json
import asyncio
from datetime import datetime
from typing import Dict, Any

def main():
    print("🔍 PRODUCTION ZEP DIAGNOSTIC")
    print("=" * 60)
    print(f"🕐 Started at: {datetime.now().isoformat()}")
    print()
    
    # Step 1: Environment Validation
    print("1️⃣ ENVIRONMENT VALIDATION")
    print("-" * 30)
    
    zep_api_key = os.getenv("ZEP_API_KEY")
    zep_api_url = os.getenv("ZEP_API_URL", "https://api.getzep.com")
    
    if not zep_api_key:
        print("❌ CRITICAL: ZEP_API_KEY not set in production environment")
        print("   💡 Fix: Set ZEP_API_KEY environment variable")
        return False
    
    print(f"✅ ZEP_API_KEY present: {zep_api_key[:8]}...{zep_api_key[-4:]}")
    print(f"✅ ZEP_API_URL: {zep_api_url}")
    
    # Step 2: Zep SDK Import Test
    print("\n2️⃣ ZEP SDK AVAILABILITY")
    print("-" * 30)
    
    try:
        from zep_cloud.client import Zep
        print("✅ Zep SDK imported successfully")
    except ImportError as e:
        print(f"❌ CRITICAL: Cannot import Zep SDK: {e}")
        print("   💡 Fix: pip install zep-cloud")
        return False
    
    # Step 3: Zep Client Creation Test
    print("\n3️⃣ ZEP CLIENT CREATION")
    print("-" * 30)
    
    try:
        client = Zep(base_url=zep_api_url, api_key=zep_api_key)
        print("✅ Zep client created successfully")
    except Exception as e:
        print(f"❌ CRITICAL: Cannot create Zep client: {e}")
        print("   💡 Fix: Check API key format and URL")
        return False
    
    # Step 4: Basic API Connectivity Test
    print("\n4️⃣ ZEP API CONNECTIVITY")
    print("-" * 30)
    
    try:
        # Test basic API connectivity
        users_response = client.user.list_ordered(page_size=1)
        print("✅ Zep API is reachable and responding")
        user_count = len(users_response.users) if users_response.users else 0
        print(f"   📊 Current user count in Zep: {user_count}")
    except Exception as e:
        error_str = str(e)
        print(f"❌ CRITICAL: Zep API connection failed: {error_str}")
        
        # Specific error analysis
        if "401" in error_str or "unauthorized" in error_str.lower():
            print("   🔍 ISSUE: Authentication failure")
            print("   💡 Fix: Check if API key is valid and has correct permissions")
        elif "403" in error_str or "forbidden" in error_str.lower():
            print("   🔍 ISSUE: Permission denied")
            print("   💡 Fix: API key may not have user management permissions")
        elif "timeout" in error_str.lower() or "network" in error_str.lower():
            print("   🔍 ISSUE: Network connectivity problem")
            print("   💡 Fix: Check firewall/network configuration")
        else:
            print(f"   🔍 ISSUE: Unknown API error: {error_str}")
        
        return False
    
    # Step 5: Circuit Breaker Status Check
    print("\n5️⃣ CIRCUIT BREAKER STATUS")
    print("-" * 30)
    
    try:
        # Import circuit breaker modules to check status
        import circuit_breaker
        from zep_memory import zep_memory
        
        # Check if circuit breakers exist and their states
        if hasattr(circuit_breaker, '_breakers'):
            breakers = circuit_breaker._breakers
            for name, breaker in breakers.items():
                if 'zep' in name.lower():
                    state = getattr(breaker, 'state', 'unknown')
                    failure_count = getattr(breaker, 'failure_count', 0)
                    print(f"   🔧 {name}: {state} (failures: {failure_count})")
                    
                    if state == 'OPEN':
                        print(f"   ❌ CRITICAL: Circuit breaker {name} is OPEN")
                        print("   💡 Fix: Reset circuit breaker or wait for recovery timeout")
        else:
            print("   ⚠️ Circuit breaker status not available")
            
    except Exception as e:
        print(f"   ⚠️ Cannot check circuit breaker status: {e}")
    
    # Step 6: Test User Creation Flow
    print("\n6️⃣ USER CREATION TEST")
    print("-" * 30)
    
    test_user_id = f"prod_diagnostic_{int(datetime.now().timestamp())}"
    
    try:
        # Test minimal user creation (what production does)
        user = client.user.add(
            user_id=test_user_id,
            metadata={
                "user_type": "business_owner",
                "source": "diagnostic_test"
            }
        )
        print(f"✅ User creation successful: {user.user_id}")
        
        # Verify user exists
        retrieved_user = client.user.get(test_user_id)
        print(f"✅ User retrieval successful: {retrieved_user.user_id}")
        
        print("\n🎉 DIAGNOSTIC RESULT: ZEP INTEGRATION IS WORKING")
        print("   💭 The issue may be in the application code, not Zep API")
        
        return True
        
    except Exception as e:
        error_str = str(e)
        print(f"❌ CRITICAL: User creation failed: {error_str}")
        
        # Detailed error analysis
        if "duplicate" in error_str.lower() or "already exists" in error_str.lower():
            print("   🔍 ISSUE: User ID collision (not critical)")
            print("   💡 This suggests the API is working, just user ID conflict")
        elif "invalid" in error_str.lower() and "user_id" in error_str.lower():
            print("   🔍 ISSUE: Invalid user ID format")
            print("   💡 Fix: Check user ID format requirements")
        elif "quota" in error_str.lower() or "limit" in error_str.lower():
            print("   🔍 ISSUE: API quota or rate limit exceeded")
            print("   💡 Fix: Check Zep account limits")
        else:
            print(f"   🔍 ISSUE: Unknown user creation error")
        
        return False

def check_production_config():
    """Additional production configuration checks"""
    print("\n7️⃣ PRODUCTION CONFIG ANALYSIS")
    print("-" * 30)
    
    issues_found = []
    
    # Check for common production environment issues
    if not os.getenv("ENVIRONMENT"):
        issues_found.append("ENVIRONMENT variable not set")
    
    # Check logging configuration
    log_level = os.getenv("LOG_LEVEL", "INFO")
    if log_level != "DEBUG":
        print(f"   ℹ️ Log level is {log_level} (consider DEBUG for troubleshooting)")
    
    # Check for database connections that might affect performance
    neo4j_uri = os.getenv("NEO4J_URI")
    if not neo4j_uri:
        issues_found.append("NEO4J_URI not configured")
    
    supabase_url = os.getenv("SUPABASE_URL")
    if not supabase_url:
        issues_found.append("SUPABASE_URL not configured")
    
    if issues_found:
        print("   ⚠️ Configuration issues found:")
        for issue in issues_found:
            print(f"      - {issue}")
    else:
        print("   ✅ Production configuration looks good")

def generate_fix_recommendations():
    """Generate specific fix recommendations based on findings"""
    print("\n🔧 FIX RECOMMENDATIONS")
    print("=" * 60)
    
    print("Based on diagnostic results, try these fixes in order:")
    print()
    print("1. **If Circuit Breaker is OPEN:**")
    print("   - Wait 30 seconds for automatic recovery")
    print("   - Or restart the application to reset circuit breakers")
    print()
    print("2. **If Authentication Failed:**")
    print("   - Verify ZEP_API_KEY is correctly set in production")
    print("   - Check API key permissions in Zep dashboard")
    print("   - Test API key with curl:")
    print("     curl -H 'Authorization: Api-Key YOUR_KEY' https://api.getzep.com/api/v2/users")
    print()
    print("3. **If Network Issues:**")
    print("   - Check firewall rules allow HTTPS to api.getzep.com")
    print("   - Verify DNS resolution works: nslookup api.getzep.com")
    print()
    print("4. **If User Creation Works in Diagnostic:**")
    print("   - Check application logs for specific error details")
    print("   - Verify questionnaire service is calling correct methods")
    print("   - Check if user metadata format is valid")

if __name__ == "__main__":
    try:
        success = main()
        check_production_config()
        generate_fix_recommendations()
        
        print(f"\n📊 DIAGNOSTIC RESULT: {'✅ PASSED' if success else '❌ FAILED'}")
        
        if not success:
            print("\n🚨 IMMEDIATE ACTIONS NEEDED:")
            print("1. Fix the critical issues identified above")
            print("2. Re-run this diagnostic script")
            print("3. Test questionnaire flow after fixes")
        else:
            print("\n✅ ZEP API IS WORKING - Check application logs for specific errors")
            
    except Exception as e:
        print(f"\n💥 DIAGNOSTIC SCRIPT ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)