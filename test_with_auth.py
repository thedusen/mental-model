#!/usr/bin/env python3
"""
Health Check with Proper Supabase Authentication

This script tests the questionnaire system using real Supabase authentication.
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

from supabase import create_client, Client
from zep_memory import zep_service

# Load environment variables
SUPABASE_URL = "http://localhost:54321"
SUPABASE_SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImV4cCI6MTk4MzgxMjk5Nn0.EGIM96RAZx35lJzdJsyH-qQwv8Hdp7fsn3W0YpN81IU"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0"


class AuthenticatedHealthChecker:
    def __init__(self):
        # Use service role for admin operations
        self.admin_client: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        # Use anon client for user operations
        self.user_client: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        self.test_user = None
        self.test_session = None

    async def run_authenticated_test(self):
        """Run health check with proper authentication"""
        print("🔐 Starting Authenticated Health Check...\n")

        try:
            # Step 1: Create authenticated user
            await self.create_test_user()

            # Step 2: Test questionnaire flow with auth
            await self.test_authenticated_questionnaire()

            # Step 3: Test Zep integration
            await self.test_zep_with_auth()

            # Step 4: Test context retrieval
            await self.test_context_with_auth()

            # Step 5: Test chat integration (simulation)
            await self.simulate_chat_integration()

        finally:
            # Cleanup
            await self.cleanup_test_user()

        print("\n✅ Authenticated health check completed!")

    async def create_test_user(self):
        """Create a test user using Supabase Auth"""
        print("👤 Creating authenticated test user...")

        test_email = f"healthcheck+{uuid.uuid4().hex[:8]}@test.com"
        test_password = "testpassword123"

        try:
            # Sign up user using auth
            response = self.user_client.auth.sign_up(
                {"email": test_email, "password": test_password}
            )

            if response.user:
                self.test_user = response.user
                print(f"✅ Created test user: {test_email}")
                print(f"   User ID: {self.test_user.id}")

                # Create user profile
                profile_data = {
                    "id": self.test_user.id,
                    "email": test_email,
                    "full_name": "Health Check User",
                }

                # Use service role to bypass RLS for testing
                profile_response = (
                    self.admin_client.table("user_profiles")
                    .insert(profile_data)
                    .execute()
                )

                if profile_response.data:
                    print("✅ User profile created")
                else:
                    print("⚠️  Profile creation issue")

            else:
                print("❌ Failed to create test user")

        except Exception as e:
            print(f"❌ User creation failed: {e}")

    async def test_authenticated_questionnaire(self):
        """Test questionnaire flow with authenticated user"""
        print("📝 Testing authenticated questionnaire flow...")

        if not self.test_user:
            print("❌ No test user available")
            return

        try:
            # Get first 3 questions
            questions_response = (
                self.admin_client.table("questionnaire_questions")
                .select("*")
                .order("question_number")
                .limit(3)
                .execute()
            )
            questions = questions_response.data

            print(f"📋 Retrieved {len(questions)} questions for testing")

            # Test answers
            test_answers = [
                "Technology and AI services",
                "25-50 employees",
                "CTO and Co-founder",
            ]

            saved_count = 0
            for i, (question, answer) in enumerate(zip(questions, test_answers)):
                try:
                    # Save response using service role (bypassing RLS for test)
                    response_data = {
                        "user_id": self.test_user.id,
                        "question_id": question["id"],
                        "response_text": answer,
                        "skipped": False,
                    }

                    response = (
                        self.admin_client.table("user_questionnaire_responses")
                        .insert(response_data)
                        .execute()
                    )

                    if response.data:
                        saved_count += 1
                        print(
                            f"✅ Saved Q{question['question_number']}: {answer[:40]}..."
                        )

                        # Test Zep sync immediately after each answer
                        await self.sync_answer_to_zep(question, answer)

                    else:
                        print(f"❌ Failed to save answer {i+1}")

                except Exception as e:
                    print(f"❌ Error saving answer {i+1}: {e}")

            print(
                f"📊 Questionnaire test result: {saved_count}/{len(questions)} answers saved"
            )

            # Check progress
            progress_response = (
                self.admin_client.table("user_questionnaire_progress")
                .select("*")
                .eq("user_id", self.test_user.id)
                .execute()
            )

            if progress_response.data:
                progress = progress_response.data[0]
                print(
                    f"✅ Progress tracking works: Status={progress['status']}, Current Q={progress['current_question']}"
                )
            else:
                print("⚠️  No progress record found")

        except Exception as e:
            print(f"❌ Questionnaire test failed: {e}")

    async def sync_answer_to_zep(self, question: Dict, answer: str):
        """Test syncing individual answer to Zep"""
        try:
            if not zep_service.enabled:
                print("⚠️  Zep disabled, skipping sync")
                return

            entity_data = {
                "entity_id": f"business_profile_q{question['question_number']}",
                "entity_type": "business_profile_question",
                "question": question["question_text"],
                "answer": answer,
                "question_number": question["question_number"],
                "category": question.get("question_category", "general"),
                "answered_at": datetime.now().isoformat(),
            }

            await zep_service.add_or_update_business_context(
                self.test_user.id, entity_data
            )
            print(f"✅ Synced Q{question['question_number']} to Zep")

        except Exception as e:
            print(f"⚠️  Zep sync warning for Q{question['question_number']}: {e}")

    async def test_zep_with_auth(self):
        """Test Zep operations with authenticated user"""
        print("🧠 Testing Zep with authenticated user...")

        if not zep_service.enabled:
            print("⚠️  Zep is disabled")
            return

        if not self.test_user:
            print("❌ No test user available")
            return

        try:
            # Test user creation in Zep
            user_metadata = {
                "name": "Health Check User",
                "email": self.test_user.email,
                "business_type": "technology_startup",
            }

            zep_user = zep_service.manager.ensure_user_exists(
                self.test_user.id, user_metadata
            )

            if zep_user:
                print("✅ Zep user created/verified")
            else:
                print("⚠️  Zep user creation issue")

            # Test retrieving business context
            await asyncio.sleep(2)  # Wait for Zep to process

            business_context = await zep_service.get_business_profile_context(
                self.test_user.id
            )

            if business_context:
                print(f"✅ Retrieved business context: {business_context[:100]}...")
            else:
                print("⚠️  No business context available yet (may need more time)")

        except Exception as e:
            print(f"❌ Zep test failed: {e}")

    async def test_context_with_auth(self):
        """Test context loading for chat"""
        print("💬 Testing context loading...")

        if not self.test_user:
            print("❌ No test user available")
            return

        try:
            # Get user's questionnaire responses directly from DB
            responses = (
                self.admin_client.table("user_questionnaire_responses")
                .select("*, questionnaire_questions(question_text, question_category)")
                .eq("user_id", self.test_user.id)
                .execute()
            )

            if responses.data:
                print(f"✅ Database context: {len(responses.data)} responses available")

                # Format as chat context
                context_elements = []
                for resp in responses.data:
                    question_text = resp["questionnaire_questions"]["question_text"]
                    answer = resp["response_text"]
                    category = resp["questionnaire_questions"]["question_category"]

                    context_elements.append(f"- {category}: {question_text} → {answer}")

                business_context = "Business Profile:\n" + "\n".join(context_elements)
                print(f"✅ Formatted chat context ({len(business_context)} chars):")
                print(f"   {business_context[:150]}...")

            else:
                print("❌ No responses found for context")

            # Test Zep memory context if available
            if zep_service.enabled:
                session_id = f"test_session_{uuid.uuid4()}"

                try:
                    memory_context = zep_service.manager.get_relevant_memory(session_id)
                    if memory_context.get("has_memory"):
                        print(f"✅ Zep memory context available")
                    else:
                        print("⚠️  No Zep memory context yet")
                except Exception as e:
                    print(f"⚠️  Zep memory test: {e}")

        except Exception as e:
            print(f"❌ Context test failed: {e}")

    async def simulate_chat_integration(self):
        """Simulate how questionnaire data would be used in chat"""
        print("🎯 Simulating chat integration...")

        if not self.test_user:
            print("❌ No test user available")
            return

        try:
            # Simulate the chat flow that would happen in main.py
            user_id = self.test_user.id
            session_id = f"test_chat_{uuid.uuid4()}"
            test_query = "What are my biggest business challenges?"

            print(f"   Query: '{test_query}'")
            print(f"   User: {user_id}")
            print(f"   Session: {session_id}")

            # Step 1: Get business profile from Supabase (fallback)
            responses = (
                self.admin_client.table("user_questionnaire_responses")
                .select("*, questionnaire_questions(question_text, question_category)")
                .eq("user_id", user_id)
                .execute()
            )

            supabase_context = ""
            if responses.data:
                relevant_responses = [
                    r
                    for r in responses.data
                    if "challenge"
                    in r["questionnaire_questions"]["question_text"].lower()
                ]

                if relevant_responses:
                    for resp in relevant_responses:
                        supabase_context += (
                            f"User's Challenge: {resp['response_text']}\n"
                        )

                    print(f"✅ Supabase context found: {supabase_context.strip()}")
                else:
                    print("⚠️  No challenge-related responses found")

            # Step 2: Try Zep context
            zep_context = ""
            if zep_service.enabled:
                try:
                    business_profile = zep_service.manager.get_business_profile(user_id)
                    if business_profile and "biggest_challenge" in business_profile:
                        zep_context = f"Business Challenge: {business_profile['biggest_challenge']}"
                        print(f"✅ Zep context found: {zep_context}")
                    else:
                        print("⚠️  No Zep business profile available")
                except Exception as e:
                    print(f"⚠️  Zep context error: {e}")

            # Step 3: Combine contexts (as done in main.py)
            combined_context = ""
            if zep_context:
                combined_context = zep_context
            elif supabase_context:
                combined_context = supabase_context
            else:
                combined_context = "No specific business context available"

            print(f"✅ Final context for AI: {combined_context[:100]}...")

            # This context would be sent to Claude along with the expert knowledge graph
            print("✅ Chat integration simulation successful")

        except Exception as e:
            print(f"❌ Chat integration simulation failed: {e}")

    async def cleanup_test_user(self):
        """Clean up test user and data"""
        print("🧹 Cleaning up test user...")

        if not self.test_user:
            return

        try:
            user_id = self.test_user.id

            # Delete questionnaire data
            self.admin_client.table("user_questionnaire_responses").delete().eq(
                "user_id", user_id
            ).execute()
            self.admin_client.table("user_questionnaire_progress").delete().eq(
                "user_id", user_id
            ).execute()
            self.admin_client.table("user_profiles").delete().eq(
                "id", user_id
            ).execute()

            # Delete Zep data
            if zep_service.enabled:
                try:
                    zep_service.manager.delete_user_data(user_id)
                    print("✅ Zep data cleaned up")
                except Exception as e:
                    print(f"⚠️  Zep cleanup warning: {e}")

            # Note: We don't delete from auth.users as that requires special permissions
            print("✅ Test data cleanup completed")

        except Exception as e:
            print(f"⚠️  Cleanup warning: {e}")


async def main():
    checker = AuthenticatedHealthChecker()
    await checker.run_authenticated_test()


if __name__ == "__main__":
    asyncio.run(main())
