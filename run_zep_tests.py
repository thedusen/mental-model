#!/usr/bin/env python3
"""
Comprehensive test runner for Zep user creation fix validation
Runs all test suites to validate the business requirement:
"All authenticated users should get Zep users created automatically on their first chat interaction"
"""

import subprocess
import sys
import os
import json
from pathlib import Path
from typing import Dict, List, Tuple


class ZepTestRunner:
    """Test runner for Zep user creation fix validation"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.backend_path = self.project_root / "backend"
        self.frontend_path = self.project_root / "frontend"
        self.results = {}
        
    def run_command(self, command: List[str], cwd: Path = None) -> Tuple[bool, str]:
        """Run a command and return success status and output"""
        try:
            result = subprocess.run(
                command,
                cwd=cwd or self.project_root,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            return result.returncode == 0, result.stdout + result.stderr
            
        except subprocess.TimeoutExpired:
            return False, "Test execution timed out"
        except Exception as e:
            return False, f"Error running command: {e}"
    
    def check_dependencies(self) -> bool:
        """Check if all required dependencies are installed"""
        print("🔍 Checking test dependencies...")
        
        # Check backend dependencies
        backend_deps = [
            ("pytest", "pytest --version"),
            ("fastapi", "python -c 'import fastapi; print(fastapi.__version__)'"),
        ]
        
        # Check frontend dependencies  
        frontend_deps = [
            ("npm", "npm --version"),
            ("react-scripts", "npm list react-scripts --depth=0")
        ]
        
        all_good = True
        
        # Check backend
        for dep_name, check_cmd in backend_deps:
            success, output = self.run_command(check_cmd.split(), self.backend_path)
            if success:
                print(f"✅ Backend dependency {dep_name}: OK")
            else:
                print(f"❌ Backend dependency {dep_name}: Missing")
                all_good = False
        
        # Check frontend
        for dep_name, check_cmd in frontend_deps:
            success, output = self.run_command(check_cmd.split(), self.frontend_path)
            if success:
                print(f"✅ Frontend dependency {dep_name}: OK")
            else:
                print(f"❌ Frontend dependency {dep_name}: Missing")
                all_good = False
        
        return all_good
    
    def install_test_dependencies(self) -> bool:
        """Install missing test dependencies"""
        print("📦 Installing test dependencies...")
        
        # Install backend test dependencies
        print("Installing backend test dependencies...")
        success, output = self.run_command(
            ["pip", "install", "-r", "test_requirements.txt"],
            self.backend_path
        )
        if not success:
            print(f"❌ Failed to install backend test dependencies: {output}")
            return False
            
        # Install frontend test dependencies
        print("Installing frontend test dependencies...")
        success, output = self.run_command(
            ["npm", "install"],
            self.frontend_path
        )
        if not success:
            print(f"❌ Failed to install frontend dependencies: {output}")
            return False
            
        print("✅ All test dependencies installed")
        return True
    
    def run_backend_tests(self) -> bool:
        """Run backend API tests"""
        print("\n🧪 Running backend API tests...")
        
        # Run pytest with coverage
        success, output = self.run_command([
            "python", "-m", "pytest", 
            "tests/",
            "-v",
            "--cov=main",
            "--cov=zep_memory", 
            "--cov=supabase_client",
            "--cov-report=term-missing",
            "--tb=short"
        ], self.backend_path)
        
        self.results["backend_tests"] = {
            "success": success,
            "output": output
        }
        
        if success:
            print("✅ Backend tests passed")
        else:
            print("❌ Backend tests failed")
            print(output)
            
        return success
    
    def run_frontend_tests(self) -> bool:
        """Run frontend unit and integration tests"""
        print("\n🧪 Running frontend tests...")
        
        # Set test environment
        env = os.environ.copy()
        env["CI"] = "true"  # Prevents watch mode
        
        # Run React tests
        success, output = self.run_command([
            "npm", "run", "test:coverage"
        ], self.frontend_path)
        
        self.results["frontend_tests"] = {
            "success": success,
            "output": output
        }
        
        if success:
            print("✅ Frontend tests passed")
        else:
            print("❌ Frontend tests failed")
            print(output)
            
        return success
    
    def run_integration_tests(self) -> bool:
        """Run integration tests"""
        print("\n🔗 Running integration tests...")
        
        # Run backend integration tests
        success, output = self.run_command([
            "python", "-m", "pytest", 
            "tests/test_integration_user_flows.py",
            "-v",
            "--tb=short"
        ], self.backend_path)
        
        self.results["integration_tests"] = {
            "success": success,
            "output": output
        }
        
        if success:
            print("✅ Integration tests passed")
        else:
            print("❌ Integration tests failed")
            print(output)
            
        return success
    
    def validate_zep_user_creation_fix(self) -> bool:
        """Validate that the Zep user creation fix works correctly"""
        print("\n🎯 Validating Zep user creation fix...")
        
        # Run specific tests that validate the fix
        test_files = [
            "tests/test_chat_sessions_api.py::TestChatSessionsAPI::test_create_session_success_with_zep_user_creation",
            "tests/test_chat_sessions_api.py::TestChatSessionsAPI::test_create_session_zep_failure_continues_session_creation",
            "tests/test_integration_user_flows.py::TestCompleteUserFlows::test_direct_chat_user_flow_complete",
            "tests/test_integration_user_flows.py::TestCompleteUserFlows::test_lets_chat_button_user_flow_complete",
            "tests/test_integration_user_flows.py::TestBusinessRequirementValidation::test_all_authenticated_users_get_zep_users_requirement"
        ]
        
        all_passed = True
        for test_file in test_files:
            print(f"Running: {test_file}")
            success, output = self.run_command([
                "python", "-m", "pytest",
                test_file,
                "-v"
            ], self.backend_path)
            
            if not success:
                all_passed = False
                print(f"❌ Failed: {test_file}")
                print(output)
            else:
                print(f"✅ Passed: {test_file}")
        
        self.results["zep_fix_validation"] = {
            "success": all_passed,
            "tests_run": len(test_files)
        }
        
        return all_passed
    
    def generate_test_report(self) -> None:
        """Generate a comprehensive test report"""
        print("\n📊 Generating test report...")
        
        report = {
            "test_run_timestamp": subprocess.run(
                ["date", "-u", "+%Y-%m-%dT%H:%M:%SZ"],
                capture_output=True,
                text=True
            ).stdout.strip(),
            "summary": {
                "total_test_suites": len(self.results),
                "passed_suites": sum(1 for r in self.results.values() if r.get("success", False)),
                "failed_suites": sum(1 for r in self.results.values() if not r.get("success", False))
            },
            "results": self.results,
            "business_requirement_status": "PASSED" if self.results.get("zep_fix_validation", {}).get("success", False) else "FAILED"
        }
        
        # Write JSON report
        report_path = self.project_root / "test_report.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        
        # Print summary
        print(f"\n{'='*60}")
        print("ZEP USER CREATION FIX - TEST REPORT")
        print(f"{'='*60}")
        print(f"Test Suites Run: {report['summary']['total_test_suites']}")
        print(f"Passed: {report['summary']['passed_suites']}")
        print(f"Failed: {report['summary']['failed_suites']}")
        print(f"Business Requirement: {report['business_requirement_status']}")
        print(f"\nFull report saved to: {report_path}")
        
        if report["business_requirement_status"] == "PASSED":
            print("\n🎉 SUCCESS: All authenticated users will get Zep users created automatically!")
        else:
            print("\n⚠️  FAILURE: The fix needs additional work")
        
    def run_all_tests(self) -> bool:
        """Run all test suites"""
        print("🚀 Starting comprehensive Zep user creation fix validation")
        print("="*60)
        
        # Check and install dependencies
        if not self.check_dependencies():
            if not self.install_test_dependencies():
                print("❌ Failed to install dependencies")
                return False
        
        # Run all test suites
        test_suites = [
            ("Backend API Tests", self.run_backend_tests),
            ("Frontend Tests", self.run_frontend_tests), 
            ("Integration Tests", self.run_integration_tests),
            ("Zep Fix Validation", self.validate_zep_user_creation_fix)
        ]
        
        all_passed = True
        for suite_name, test_func in test_suites:
            print(f"\n🧪 Running {suite_name}...")
            if not test_func():
                all_passed = False
        
        # Generate report
        self.generate_test_report()
        
        return all_passed


if __name__ == "__main__":
    runner = ZepTestRunner()
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--backend-only":
            success = runner.run_backend_tests()
        elif sys.argv[1] == "--frontend-only":
            success = runner.run_frontend_tests()
        elif sys.argv[1] == "--integration-only":
            success = runner.run_integration_tests()
        elif sys.argv[1] == "--fix-validation-only":
            success = runner.validate_zep_user_creation_fix()
        else:
            print(f"Unknown option: {sys.argv[1]}")
            print("Usage: python run_zep_tests.py [--backend-only|--frontend-only|--integration-only|--fix-validation-only]")
            sys.exit(1)
    else:
        # Run all tests
        success = runner.run_all_tests()
    
    sys.exit(0 if success else 1)