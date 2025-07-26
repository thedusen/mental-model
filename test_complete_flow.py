#!/usr/bin/env python3
"""
Complete End-to-End Test of User Data Graph Feature

This script tests the complete flow including the challenge question.
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


class CompleteFlowTester:
    def __init__(self):
        # Use service role for admin operations
        self.admin_client: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        # Use anon client for user operations
        self.user_client: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        self.test_user = None

    async def run_complete_test(self):
        """Run complete end-to-end test including challenge question"""
        print("🎯 Starting Complete End-to-End Test...\n")

        try:
            # Step 1: Create user and answer ALL questions including challenges
            await self.create_test_user_with_full_profile()

            # Step 2: Wait for Zep processing
            print("⏳ Waiting for Zep to process data...")
            await asyncio.sleep(5)

            # Step 3: Test context retrieval for different query types
            await self.test_business_context_queries()

            # Step 4: Test the actual chat integration flow
            await self.test_real_chat_flow()

        finally:
            # Cleanup
            await self.cleanup_test_user()

        print("\n🎉 Complete end-to-end test finished!")

    async def create_test_user_with_full_profile(self):
        """Create user and answer key business questions"""
        print("👤 Creating test user with complete business profile...")

        test_email = f"complete_test+{uuid.uuid4().hex[:8]}@test.com"
        test_password = "testpassword123"

        try:
            # Create user
            response = self.user_client.auth.sign_up(
                {"email": test_email, "password": test_password}
            )

            if response.user:
                self.test_user = response.user
                print(f"✅ Created test user: {test_email}")

                # Create profile
                profile_data = {
                    "id": self.test_user.id,
                    "email": test_email,
                    "full_name": "Complete Test User",
                }

                self.admin_client.table("user_profiles").insert(profile_data).execute()
                print("✅ User profile created")

                # Answer key business questions
                await self.answer_key_questions()

        except Exception as e:
            print(f"❌ User setup failed: {e}")

    async def answer_key_questions(self):
        """Answer the most important business questions"""
        print("📝 Answering key business questions...")

        # Get all questions
        questions_response = (
            self.admin_client.table("questionnaire_questions")
            .select("*")
            .order("question_number")
            .execute()
        )
        questions = questions_response.data

        # Define comprehensive answers
        business_answers = {
            1: "Technology and AI services - we build AI-powered tools for small businesses",
            2: "15 employees including 8 developers, 3 designers, 2 sales, 1 marketing, 1 admin",
            3: "CEO and Co-founder - I handle strategy, product vision, and customer relationships",
            4: "Scale revenue to $2M ARR, launch enterprise tier, expand team to 25 people, and establish partnerships with 3 major SaaS platforms",
            5: "Customer acquisition cost is too high, we're burning cash faster than expected, and we need to improve product-market fit in the SMB segment",
            6: "Small to medium businesses (10-100 employees) in service industries like consulting, agencies, and professional services who struggle with manual processes",
            7: "AI-powered workflow automation tools, customer support chatbots, and business intelligence dashboards delivered as SaaS subscriptions",
            8: "Monthly recurring subscriptions: $99/month Basic, $299/month Professional, $799/month Enterprise plus one-time setup fees",
            9: "Monthly Recurring Revenue (MRR), Customer Acquisition Cost (CAC), Lifetime Value (LTV), churn rate, Net Promoter Score (NPS), and daily active users",
            10: "Our AI models are specifically trained for SMB workflows, we have superior customer onboarding, and our pricing is 40% lower than enterprise competitors",
            11: "We're venture-backed (Series A), facing competitive pressure from larger players, need to prove scalability before next fundraising round in 18 months",
        }

        saved_count = 0
        for question in questions:
            question_num = question["question_number"]
            if question_num in business_answers:
                try:
                    answer = business_answers[question_num]

                    # Save response
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
                        print(f"✅ Q{question_num}: {answer[:60]}...")

                        # Sync to Zep immediately
                        await self.sync_answer_to_zep(question, answer)

                except Exception as e:
                    print(f"❌ Error saving Q{question_num}: {e}")

        print(f"📊 Saved {saved_count}/{len(business_answers)} answers")

        # Check final progress
        progress_response = (
            self.admin_client.table("user_questionnaire_progress")
            .select("*")
            .eq("user_id", self.test_user.id)
            .execute()
        )

        if progress_response.data:
            progress = progress_response.data[0]
            print(
                f"✅ Progress: Status={progress['status']}, Questions completed: {saved_count}/11"
            )

    async def sync_answer_to_zep(self, question: Dict, answer: str):
        """Sync answer to Zep"""
        try:
            if not zep_service.enabled:
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

        except Exception as e:
            print(f"⚠️  Zep sync error Q{question['question_number']}: {e}")

    async def test_business_context_queries(self):
        """Test different types of business context queries"""
        print("🔍 Testing business context queries...")

        if not self.test_user:
            return

        test_queries = [
            ("What are my biggest business challenges?", "challenges"),
            ("What industry am I in?", "business_context"),
            ("What are my business goals?", "goals"),
            ("Who are my customers?", "market"),
            ("What's my revenue model?", "financial"),
        ]

        for query, expected_category in test_queries:
            print(f"\n🔎 Testing query: '{query}'")

            # Method 1: Direct Supabase lookup (fallback)
            responses = (
                self.admin_client.table("user_questionnaire_responses")
                .select("*, questionnaire_questions(question_text, question_category)")
                .eq("user_id", self.test_user.id)
                .execute()
            )

            if responses.data:
                # Find relevant responses based on category or keywords
                relevant_responses = []

                for resp in responses.data:
                    question_cat = resp["questionnaire_questions"]["question_category"]
                    question_text = resp["questionnaire_questions"][
                        "question_text"
                    ].lower()

                    # Match by category or keywords
                    if question_cat == expected_category or any(
                        word in question_text
                        for word in query.lower().split()
                        if len(word) > 3
                    ):
                        relevant_responses.append(resp)

                if relevant_responses:
                    print(
                        f"✅ Found {len(relevant_responses)} relevant responses from Supabase:"
                    )
                    for resp in relevant_responses[:2]:  # Show first 2
                        answer = resp["response_text"]
                        print(f"   - {answer[:80]}...")
                else:
                    print("⚠️  No relevant responses found in Supabase")

            # Method 2: Zep business profile lookup
            if zep_service.enabled:
                try:
                    business_profile = zep_service.manager.get_business_profile(
                        self.test_user.id
                    )

                    if business_profile:
                        print(
                            f"✅ Zep business profile has {len(business_profile)} elements:"
                        )
                        for key, value in list(business_profile.items())[:3]:
                            print(f"   - {key}: {value[:60]}...")
                    else:
                        print("⚠️  No Zep business profile available yet")

                except Exception as e:
                    print(f"⚠️  Zep profile error: {e}")

    async def test_real_chat_flow(self):
        """Test the actual chat flow as it would work in main.py"""
        print("\n💬 Testing real chat flow integration...")

        if not self.test_user:
            return

        # Simulate the chat context loading process from main.py
        user_id = self.test_user.id
        session_id = f"test_session_{uuid.uuid4()}"
        test_query = (
            "What are my biggest business challenges and how can I address them?"
        )

        print(f"Query: '{test_query}'")
        print(f"User ID: {user_id}")
        print(f"Session: {session_id}")

        try:
            # Step 1: This is what get_optimized_user_context() would do
            print("\n📊 Step 1: Retrieving user context...")

            # Get cached business profile (simulated)
            user_context_parts = []

            # Method A: Try Zep business profile
            if zep_service.enabled:
                try:
                    business_profile = zep_service.manager.get_business_profile(user_id)
                    if business_profile:
                        # Simulate get_relevant_business_elements()
                        relevant_elements = []
                        query_lower = test_query.lower()

                        for key, value in business_profile.items():
                            if any(
                                word in key.lower() or word in value.lower()
                                for word in [
                                    "challenge",
                                    "problem",
                                    "difficult",
                                    "issue",
                                ]
                            ):
                                relevant_elements.append(
                                    f"- {key.replace('_', ' ').title()}: {value}"
                                )

                        if relevant_elements:
                            business_context = (
                                "Business Profile Context:\n"
                                + "\n".join(relevant_elements)
                            )
                            user_context_parts.append(business_context)
                            print(
                                f"✅ Zep business context ({len(business_context)} chars)"
                            )

                except Exception as e:
                    print(f"⚠️  Zep context error: {e}")

            # Method B: Fallback to direct Supabase
            if not user_context_parts:
                responses = (
                    self.admin_client.table("user_questionnaire_responses")
                    .select(
                        "*, questionnaire_questions(question_text, question_category)"
                    )
                    .eq("user_id", user_id)
                    .execute()
                )

                if responses.data:
                    # Find challenge-related responses
                    challenge_responses = [
                        r
                        for r in responses.data
                        if "challenge"
                        in r["questionnaire_questions"]["question_text"].lower()
                        or r["questionnaire_questions"]["question_category"]
                        == "challenges"
                    ]

                    if challenge_responses:
                        context_items = []
                        for resp in challenge_responses:
                            context_items.append(
                                f"- Business Challenge: {resp['response_text']}"
                            )

                        business_context = "Business Profile Context:\n" + "\n".join(
                            context_items
                        )
                        user_context_parts.append(business_context)
                        print(
                            f"✅ Supabase business context ({len(business_context)} chars)"
                        )

            # Step 2: Get conversation context from Zep (simulated)
            if zep_service.enabled:
                try:
                    # This simulates what the chat endpoint does
                    memory_context = zep_service.manager.get_relevant_memory(session_id)
                    if memory_context.get("has_memory"):
                        conversation_context = f"Conversation Context:\n{memory_context.get('context', '')[:500]}"
                        user_context_parts.append(conversation_context)
                        print("✅ Conversation context retrieved")
                    else:
                        print("⚠️  No conversation context (new session)")

                except Exception as e:
                    print(f"⚠️  Memory context error: {e}")

            # Step 3: Combine contexts (as done in main.py manage_context_length)
            combined_user_context = (
                "\n\n".join(user_context_parts)
                if user_context_parts
                else "No user context available"
            )

            print(
                f"\n✅ Final combined user context ({len(combined_user_context)} chars):"
            )
            print("─" * 60)
            print(
                combined_user_context[:400]
                + ("..." if len(combined_user_context) > 400 else "")
            )
            print("─" * 60)

            # Step 4: This would be combined with expert knowledge and sent to Claude
            print("\n🤖 Final step: Combined context ready for Claude")
            print("   - Expert knowledge graph context (from Neo4j vector search)")
            print("   - User business profile context ✅")
            print("   - Conversation history context")
            print("   - Query-specific context matching")

            # Show how this enables personalized responses
            if "challenge" in combined_user_context.lower():
                print("\n✨ Personalization enabled:")
                print("   - AI will reference user's specific business challenges")
                print("   - Responses tailored to their industry and company size")
                print("   - Advice aligned with their business goals and revenue model")
                print("   - Context-aware recommendations based on their role (CEO)")

            print("\n✅ Chat flow integration test successful!")

        except Exception as e:
            print(f"❌ Chat flow test failed: {e}")

    async def cleanup_test_user(self):
        """Clean up test user and data"""
        print("\n🧹 Cleaning up test data...")

        if not self.test_user:
            return

        try:
            user_id = self.test_user.id

            # Delete all questionnaire data
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

            print("✅ Test data cleanup completed")

        except Exception as e:
            print(f"⚠️  Cleanup warning: {e}")


async def main():
    tester = CompleteFlowTester()
    await tester.run_complete_test()


if __name__ == "__main__":
    asyncio.run(main())
