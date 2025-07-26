#!/usr/bin/env python3
"""
Health Check Script for User Data Graph Feature

This script verifies all components of the questionnaire → Supabase → Zep → Chat context flow.
"""

import os
import sys
import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional

# Add the backend directory to the path
sys.path.append("backend")

# Import our backend modules
from supabase_client import SupabaseService
from zep_memory import zep_service, ZepMemoryService
from questionnaire_service import questionnaire_service

# Test constants
TEST_USER_ID = str(uuid.uuid4())
TEST_SESSION_ID = str(uuid.uuid4())
TEST_EMAIL = "test@healthcheck.com"
TEST_BUSINESS_NAME = "Health Check Corp"


class HealthChecker:
    def __init__(self):
        self.supabase = SupabaseService()
        self.zep = zep_service
        self.questionnaire = questionnaire_service
        self.results = {}

    async def run_all_tests(self):
        """Run all health check tests"""
        print("🔍 Starting User Data Graph Health Check...\n")

        # Test 1: Setup and Connections
        await self.test_supabase_connection()
        await self.test_zep_connection()

        # Test 2: Database Schema
        await self.test_questionnaire_schema()

        # Test 3: Question Management
        await self.setup_test_questions()
        await self.test_question_retrieval()

        # Test 4: User Management
        await self.test_user_creation()

        # Test 5: Questionnaire Flow
        await self.test_questionnaire_flow()

        # Test 6: Zep Integration
        await self.test_zep_integration()

        # Test 7: Context Loading
        await self.test_context_loading()

        # Test 8: Cleanup
        await self.cleanup_test_data()

        # Summary
        self.print_summary()

    async def test_supabase_connection(self):
        """Test Supabase database connection"""
        print("📊 Testing Supabase connection...")
        try:
            # Test basic connection with a simple query
            response = (
                self.supabase.client.from_("questionnaire_questions")
                .select("count")
                .execute()
            )
            self.results["supabase_connection"] = True
            print("✅ Supabase connection successful")
        except Exception as e:
            self.results["supabase_connection"] = False
            print(f"❌ Supabase connection failed: {e}")

    async def test_zep_connection(self):
        """Test Zep service connection"""
        print("🧠 Testing Zep connection...")
        try:
            if not self.zep.enabled:
                print("⚠️  Zep service is disabled")
                self.results["zep_connection"] = "disabled"
                return

            # Try to ensure a test user exists
            test_user = self.zep.manager.ensure_user_exists(
                f"test_{uuid.uuid4()}", {"name": "Test User"}
            )
            self.results["zep_connection"] = True
            print("✅ Zep connection successful")
        except Exception as e:
            self.results["zep_connection"] = False
            print(f"❌ Zep connection failed: {e}")

    async def test_questionnaire_schema(self):
        """Test that all required database tables exist"""
        print("🗄️  Testing database schema...")
        try:
            tables_to_check = [
                "questionnaire_questions",
                "user_questionnaire_responses",
                "user_questionnaire_progress",
                "user_profiles",
            ]

            schema_results = {}
            for table in tables_to_check:
                try:
                    response = (
                        self.supabase.client.from_(table).select("*").limit(1).execute()
                    )
                    schema_results[table] = True
                    print(f"✅ Table '{table}' exists and accessible")
                except Exception as e:
                    schema_results[table] = False
                    print(f"❌ Table '{table}' issue: {e}")

            self.results["schema"] = schema_results

        except Exception as e:
            self.results["schema"] = False
            print(f"❌ Schema test failed: {e}")

    async def setup_test_questions(self):
        """Manually insert the 11 questionnaire questions if they don't exist"""
        print("❓ Setting up test questions...")
        try:
            # Check if questions already exist
            response = (
                self.supabase.client.from_("questionnaire_questions")
                .select("*")
                .execute()
            )

            if len(response.data) < 11:
                print("📝 Inserting questionnaire questions...")
                questions = [
                    (1, "What industry is your business in?", "business_context"),
                    (
                        2,
                        "What is the size of your company (number of employees)?",
                        "business_context",
                    ),
                    (3, "What is your role in the company?", "personal_context"),
                    (
                        4,
                        "What are your primary business goals for the next 12 months?",
                        "goals",
                    ),
                    (
                        5,
                        "What are the biggest challenges your business currently faces?",
                        "challenges",
                    ),
                    (6, "Who is your target customer or market?", "market"),
                    (
                        7,
                        "What products or services does your business offer?",
                        "offerings",
                    ),
                    (8, "What is your current revenue model?", "financial"),
                    (9, "What key metrics do you track to measure success?", "metrics"),
                    (10, "What is your competitive advantage?", "strategy"),
                    (
                        11,
                        "What additional context would help me better understand your business?",
                        "context",
                    ),
                ]

                for question_number, question_text, category in questions:
                    try:
                        self.supabase.client.from_("questionnaire_questions").insert(
                            {
                                "question_number": question_number,
                                "question_text": question_text,
                                "question_category": category,
                            }
                        ).execute()
                        print(f"✅ Inserted question {question_number}")
                    except Exception as e:
                        print(f"⚠️  Question {question_number} might already exist: {e}")
            else:
                print("✅ Questions already exist")

            self.results["questions_setup"] = True

        except Exception as e:
            self.results["questions_setup"] = False
            print(f"❌ Questions setup failed: {e}")

    async def test_question_retrieval(self):
        """Test retrieving questionnaire questions"""
        print("📋 Testing question retrieval...")
        try:
            response = (
                self.supabase.client.from_("questionnaire_questions")
                .select("*")
                .order("question_number")
                .execute()
            )
            questions = response.data

            if len(questions) >= 11:
                print(f"✅ Retrieved {len(questions)} questions successfully")
                self.results["question_retrieval"] = True

                # Show first few questions
                for q in questions[:3]:
                    print(f"  Q{q['question_number']}: {q['question_text'][:50]}...")
            else:
                print(f"❌ Expected 11 questions, got {len(questions)}")
                self.results["question_retrieval"] = False

        except Exception as e:
            self.results["question_retrieval"] = False
            print(f"❌ Question retrieval failed: {e}")

    async def test_user_creation(self):
        """Test creating a test user profile"""
        print("👤 Testing user creation...")
        try:
            # Create test user profile
            user_data = {
                "id": TEST_USER_ID,
                "email": TEST_EMAIL,
                "full_name": "Health Check User",
                "preferences": {"test": True},
            }

            response = (
                self.supabase.client.from_("user_profiles").insert(user_data).execute()
            )

            if response.data:
                print("✅ Test user created successfully")
                self.results["user_creation"] = True
            else:
                print("❌ User creation returned no data")
                self.results["user_creation"] = False

        except Exception as e:
            self.results["user_creation"] = False
            print(f"❌ User creation failed: {e}")

    async def test_questionnaire_flow(self):
        """Test the complete questionnaire answer flow"""
        print("📝 Testing questionnaire flow...")
        try:
            # Get first question
            questions_response = (
                self.supabase.client.from_("questionnaire_questions")
                .select("*")
                .order("question_number")
                .limit(3)
                .execute()
            )
            questions = questions_response.data

            if not questions:
                print("❌ No questions available for testing")
                self.results["questionnaire_flow"] = False
                return

            # Test answering first 3 questions
            test_answers = [
                "Technology and software development",
                "15-20 employees",
                "CEO and Founder",
            ]

            saved_responses = []
            for i, (question, answer) in enumerate(zip(questions[:3], test_answers)):
                try:
                    # Save response to database
                    response_data = {
                        "user_id": TEST_USER_ID,
                        "question_id": question["id"],
                        "response_text": answer,
                        "skipped": False,
                    }

                    response = (
                        self.supabase.client.from_("user_questionnaire_responses")
                        .insert(response_data)
                        .execute()
                    )

                    if response.data:
                        saved_responses.append(response.data[0])
                        print(f"✅ Saved answer {i+1}: {answer[:30]}...")
                    else:
                        print(f"❌ Failed to save answer {i+1}")

                except Exception as e:
                    print(f"❌ Error saving answer {i+1}: {e}")

            # Check progress tracking
            try:
                progress_response = (
                    self.supabase.client.from_("user_questionnaire_progress")
                    .select("*")
                    .eq("user_id", TEST_USER_ID)
                    .execute()
                )

                if progress_response.data:
                    progress = progress_response.data[0]
                    print(
                        f"✅ Progress tracked: {progress['status']}, current question: {progress['current_question']}"
                    )
                else:
                    print("⚠️  No progress record found (might be created by trigger)")

            except Exception as e:
                print(f"⚠️  Progress check failed: {e}")

            self.results["questionnaire_flow"] = len(saved_responses) == 3
            print(f"✅ Questionnaire flow test: {len(saved_responses)}/3 answers saved")

        except Exception as e:
            self.results["questionnaire_flow"] = False
            print(f"❌ Questionnaire flow test failed: {e}")

    async def test_zep_integration(self):
        """Test Zep integration with questionnaire data"""
        print("🧠 Testing Zep integration...")
        try:
            if not self.zep.enabled:
                print("⚠️  Zep is disabled, skipping integration test")
                self.results["zep_integration"] = "disabled"
                return

            # Test syncing a questionnaire answer to Zep
            test_entity_data = {
                "entity_id": "business_profile_q1",
                "entity_type": "business_profile_question",
                "question": "What industry is your business in?",
                "answer": "Technology and software development",
                "question_number": 1,
                "category": "business_context",
                "answered_at": datetime.now().isoformat(),
            }

            # Try to sync to Zep
            await self.zep.add_or_update_business_context(
                TEST_USER_ID, test_entity_data
            )
            print("✅ Successfully synced test data to Zep")

            # Try to retrieve business profile context
            business_context = await self.zep.get_business_profile_context(TEST_USER_ID)

            if business_context:
                print(
                    f"✅ Retrieved business context from Zep: {business_context[:100]}..."
                )
                self.results["zep_integration"] = True
            else:
                print(
                    "⚠️  No business context retrieved from Zep yet (may need time to process)"
                )
                self.results["zep_integration"] = "partial"

        except Exception as e:
            self.results["zep_integration"] = False
            print(f"❌ Zep integration test failed: {e}")

    async def test_context_loading(self):
        """Test loading questionnaire data into chat context"""
        print("💬 Testing context loading...")
        try:
            # This would normally be tested through the main chat API
            # For now, let's test the business profile retrieval

            if self.zep.enabled:
                # Test getting business profile
                business_profile = self.zep.manager.get_business_profile(TEST_USER_ID)

                if business_profile:
                    print(
                        f"✅ Business profile loaded for context: {list(business_profile.keys())}"
                    )
                    self.results["context_loading"] = True
                else:
                    print("⚠️  No business profile context available yet")
                    self.results["context_loading"] = "partial"
            else:
                # Test direct Supabase retrieval as fallback
                responses = (
                    self.supabase.client.from_("user_questionnaire_responses")
                    .select(
                        "*, questionnaire_questions(question_text, question_category)"
                    )
                    .eq("user_id", TEST_USER_ID)
                    .execute()
                )

                if responses.data:
                    print(
                        f"✅ Retrieved {len(responses.data)} questionnaire responses for context"
                    )
                    self.results["context_loading"] = True

                    # Show sample context
                    for resp in responses.data[:2]:
                        print(
                            f"  - {resp['questionnaire_questions']['question_text'][:30]}...: {resp['response_text'][:30]}..."
                        )
                else:
                    print("❌ No questionnaire responses found for context")
                    self.results["context_loading"] = False

        except Exception as e:
            self.results["context_loading"] = False
            print(f"❌ Context loading test failed: {e}")

    async def cleanup_test_data(self):
        """Clean up test data"""
        print("🧹 Cleaning up test data...")
        try:
            # Delete test responses
            self.supabase.client.from_("user_questionnaire_responses").delete().eq(
                "user_id", TEST_USER_ID
            ).execute()

            # Delete test progress
            self.supabase.client.from_("user_questionnaire_progress").delete().eq(
                "user_id", TEST_USER_ID
            ).execute()

            # Delete test user
            self.supabase.client.from_("user_profiles").delete().eq(
                "id", TEST_USER_ID
            ).execute()

            # Clean up Zep data if enabled
            if self.zep.enabled:
                try:
                    self.zep.manager.delete_user_data(TEST_USER_ID)
                    print("✅ Cleaned up Zep test data")
                except Exception as e:
                    print(f"⚠️  Zep cleanup warning: {e}")

            print("✅ Test data cleanup completed")
            self.results["cleanup"] = True

        except Exception as e:
            self.results["cleanup"] = False
            print(f"❌ Cleanup failed: {e}")

    def print_summary(self):
        """Print test results summary"""
        print("\n" + "=" * 60)
        print("📊 HEALTH CHECK SUMMARY")
        print("=" * 60)

        passed = 0
        total = 0

        for test_name, result in self.results.items():
            total += 1
            status_emoji = (
                "✅"
                if result is True
                else ("⚠️" if result == "partial" or result == "disabled" else "❌")
            )
            status_text = (
                str(result)
                if result != True and result != False
                else ("PASS" if result else "FAIL")
            )

            if result is True:
                passed += 1
            elif result == "partial":
                passed += 0.5

            print(
                f"{status_emoji} {test_name.replace('_', ' ').title()}: {status_text}"
            )

        print("-" * 60)
        print(f"🎯 Overall Score: {passed}/{total} ({passed/total*100:.1f}%)")

        if passed == total:
            print("🎉 All systems are functioning correctly!")
        elif passed >= total * 0.8:
            print("✨ System is largely functional with minor issues")
        elif passed >= total * 0.6:
            print("⚠️  System has some issues that should be addressed")
        else:
            print("🚨 System has significant issues requiring attention")

        print("=" * 60)


async def main():
    """Main function to run health checks"""
    checker = HealthChecker()
    await checker.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
