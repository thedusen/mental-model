#!/usr/bin/env python3
"""
Zep API Key Validator
Validates Zep API key and provides detailed diagnostics
"""

import os
import logging
from typing import Dict, Any, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class ZepApiValidator:
    """Validates Zep API configuration and connectivity"""

    def __init__(self, api_key: str = None, api_url: str = None):
        self.api_key = api_key or os.getenv("ZEP_API_KEY")
        self.api_url = api_url or os.getenv("ZEP_API_URL", "https://api.getzep.com")

    def validate_api_key_format(self) -> Tuple[bool, str]:
        """
        Validate the format of the Zep API key

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not self.api_key:
            return False, "ZEP_API_KEY is not set"

        # Zep API keys typically start with 'zep_' or 'z_'
        if not (self.api_key.startswith("zep_") or self.api_key.startswith("z_")):
            return False, "API key should start with 'zep_' or 'z_'"

        # Check minimum length (Zep keys are typically long)
        if len(self.api_key) < 20:
            return False, f"API key appears too short ({len(self.api_key)} chars)"

        # Check for common copy-paste errors
        if "\n" in self.api_key or "\r" in self.api_key:
            return False, "API key contains newline characters"

        if self.api_key.startswith(" ") or self.api_key.endswith(" "):
            return False, "API key has leading/trailing whitespace"

        return True, "API key format appears valid"

    def test_api_connectivity(self) -> Dict[str, Any]:
        """
        Test actual API connectivity with detailed error reporting

        Returns:
            Dictionary with test results
        """
        result = {"success": False, "error": None, "details": {}, "recommendations": []}

        try:
            from zep_cloud.client import Zep

            # Create client
            client = Zep(base_url=self.api_url, api_key=self.api_key)

            # Test basic API call
            users_response = client.user.list_ordered()

            result["success"] = True
            result["details"]["api_url"] = self.api_url
            result["details"]["response_type"] = str(type(users_response))

            # Check if users exist
            if hasattr(users_response, "users"):
                user_count = len(users_response.users) if users_response.users else 0
                result["details"]["existing_users"] = user_count

                if user_count == 0:
                    result["recommendations"].append(
                        "No users found - this is expected for new Zep projects"
                    )
                else:
                    result["details"]["sample_users"] = [
                        user.user_id for user in users_response.users[:3]
                    ]

            logger.info("Zep API connectivity test successful")

        except Exception as e:
            result["error"] = str(e)
            error_lower = str(e).lower()

            # Provide specific guidance based on error type
            if "401" in error_lower or "unauthorized" in error_lower:
                result["recommendations"].extend(
                    [
                        "API key is invalid or expired",
                        "Generate a new API key from Zep Cloud dashboard",
                        "Ensure API key has proper permissions",
                    ]
                )
            elif "403" in error_lower or "forbidden" in error_lower:
                result["recommendations"].extend(
                    [
                        "API key doesn't have required permissions",
                        "Check API key scope in Zep dashboard",
                    ]
                )
            elif "404" in error_lower or "not found" in error_lower:
                result["recommendations"].extend(
                    ["Check ZEP_API_URL is correct", "Verify API endpoint exists"]
                )
            elif "timeout" in error_lower or "connection" in error_lower:
                result["recommendations"].extend(
                    [
                        "Network connectivity issue",
                        "Check firewall and network settings",
                        "Verify ZEP_API_URL is reachable",
                    ]
                )
            else:
                result["recommendations"].append(
                    "Unexpected error - check Zep service status"
                )

            logger.error(f"Zep API connectivity test failed: {e}")

        return result

    def test_user_creation(self) -> Dict[str, Any]:
        """
        Test user creation functionality

        Returns:
            Dictionary with creation test results
        """
        result = {
            "success": False,
            "error": None,
            "test_user_id": None,
            "cleanup_success": False,
        }

        try:
            from zep_cloud.client import Zep

            client = Zep(base_url=self.api_url, api_key=self.api_key)

            # Create test user
            test_user_id = f"test_validator_{int(datetime.now().timestamp())}"
            test_user_data = {
                "user_id": test_user_id,
                "email": f"{test_user_id}@test.example.com",
                "first_name": "Test",
                "last_name": "User",
                "metadata": {"source": "api_validator", "test": True},
            }

            # Create user
            created_user = client.user.add(**test_user_data)
            result["test_user_id"] = test_user_id

            # Verify user exists
            retrieved_user = client.user.get(test_user_id)

            if retrieved_user.user_id == test_user_id:
                result["success"] = True
                logger.info(f"User creation test successful: {test_user_id}")

                # Clean up test user
                try:
                    client.user.delete(test_user_id)
                    result["cleanup_success"] = True
                    logger.info(f"Test user cleanup successful: {test_user_id}")
                except Exception as cleanup_error:
                    logger.warning(f"Test user cleanup failed: {cleanup_error}")
            else:
                result["error"] = "User creation succeeded but retrieval failed"

        except Exception as e:
            result["error"] = str(e)
            logger.error(f"User creation test failed: {e}")

        return result

    def run_complete_validation(self) -> Dict[str, Any]:
        """
        Run complete validation suite

        Returns:
            Comprehensive validation results
        """
        validation_results = {
            "timestamp": datetime.now().isoformat(),
            "api_key_format": {},
            "connectivity": {},
            "user_creation": {},
            "overall_status": "unknown",
            "next_steps": [],
        }

        # Test 1: API key format
        format_valid, format_message = self.validate_api_key_format()
        validation_results["api_key_format"] = {
            "valid": format_valid,
            "message": format_message,
        }

        if not format_valid:
            validation_results["overall_status"] = "failed"
            validation_results["next_steps"].append("Fix API key format issues")
            return validation_results

        # Test 2: API connectivity
        connectivity_result = self.test_api_connectivity()
        validation_results["connectivity"] = connectivity_result

        if not connectivity_result["success"]:
            validation_results["overall_status"] = "failed"
            validation_results["next_steps"].extend(
                connectivity_result["recommendations"]
            )
            return validation_results

        # Test 3: User creation (only if connectivity works)
        creation_result = self.test_user_creation()
        validation_results["user_creation"] = creation_result

        if creation_result["success"]:
            validation_results["overall_status"] = "success"
            validation_results["next_steps"].append(
                "All tests passed - Zep integration is working"
            )
        else:
            validation_results["overall_status"] = "partial"
            validation_results["next_steps"].append(
                "Connectivity works but user creation failed"
            )

        return validation_results


def main():
    """Command line interface for Zep validation"""
    import json

    print("🔍 Zep API Validation Suite")
    print("=" * 50)

    validator = ZepApiValidator()
    results = validator.run_complete_validation()

    # Display results
    print(f"\n📊 Validation Results ({results['timestamp']})")
    print("=" * 50)

    # API Key Format
    format_result = results["api_key_format"]
    format_status = "✅" if format_result["valid"] else "❌"
    print(f"{format_status} API Key Format: {format_result['message']}")

    # Connectivity
    conn_result = results["connectivity"]
    conn_status = "✅" if conn_result["success"] else "❌"
    print(
        f"{conn_status} API Connectivity: {'Success' if conn_result['success'] else conn_result['error']}"
    )

    if conn_result["success"] and "existing_users" in conn_result["details"]:
        print(f"   📈 Existing users: {conn_result['details']['existing_users']}")

    # User Creation
    creation_result = results["user_creation"]
    if creation_result:
        creation_status = "✅" if creation_result["success"] else "❌"
        creation_msg = (
            "Success"
            if creation_result["success"]
            else creation_result.get("error", "Failed")
        )
        print(f"{creation_status} User Creation: {creation_msg}")

    # Overall Status
    status_emoji = {"success": "🎉", "partial": "⚠️", "failed": "❌", "unknown": "❓"}

    overall_status = results["overall_status"]
    print(f"\n{status_emoji[overall_status]} Overall Status: {overall_status.upper()}")

    # Next Steps
    if results["next_steps"]:
        print(f"\n📋 Next Steps:")
        for i, step in enumerate(results["next_steps"], 1):
            print(f"   {i}. {step}")

    # Detailed results
    print(f"\n📄 Detailed Results:")
    print(json.dumps(results, indent=2, default=str))

    return results["overall_status"] == "success"


if __name__ == "__main__":
    import sys

    success = main()
    sys.exit(0 if success else 1)
