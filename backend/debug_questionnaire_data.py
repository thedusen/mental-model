#!/usr/bin/env python3
"""
Debug script to verify questionnaire answers were saved properly in both database and Zep
"""

import os
import asyncio
from datetime import datetime, timedelta
from supabase_client import SupabaseService
from zep_memory import zep_service


async def check_recent_questionnaire_data():
    """Check recent questionnaire responses and Zep data"""

    print("🔍 Checking recent questionnaire data...")
    print("=" * 60)

    supabase = SupabaseService()

    try:
        # Get recent questionnaire responses (last 24 hours)
        print("\n📊 Recent Questionnaire Responses (last 24 hours):")
        print("-" * 50)

        yesterday = (datetime.now() - timedelta(days=1)).isoformat()

        response = (
            supabase.client.table("user_questionnaire_responses")
            .select("*, questionnaire_questions(question_text, question_number)")
            .gte("created_at", yesterday)
            .order("created_at", desc=True)
            .limit(50)
            .execute()
        )

        if not response.data:
            print("❌ No recent questionnaire responses found")
        else:
            users_found = set()
            for resp in response.data:
                user_id = resp["user_id"]
                users_found.add(user_id)
                question_info = resp.get("questionnaire_questions", {})

                print(f"  👤 User: {user_id[:8]}...")
                print(
                    f"     📝 Q{question_info.get('question_number', 'Unknown')}: {question_info.get('question_text', 'Unknown question')[:60]}..."
                )
                print(f"     💬 Answer: {resp['response_text'][:80]}...")
                print(f"     ⏰ Created: {resp['created_at']}")
                print(f"     🔄 Skipped: {resp['skipped']}")
                print()

            print(f"📈 Total responses: {len(response.data)}")
            print(f"👥 Unique users: {len(users_found)}")

            # Check progress for these users
            print(f"\n📊 Questionnaire Progress for Recent Users:")
            print("-" * 50)

            for user_id in users_found:
                progress_response = (
                    supabase.client.table("user_questionnaire_progress")
                    .select("*")
                    .eq("user_id", user_id)
                    .single()
                    .execute()
                )

                if progress_response.data:
                    prog = progress_response.data
                    print(f"  👤 User: {user_id[:8]}...")
                    print(f"     📊 Status: {prog['status']}")
                    print(f"     📝 Current Question: {prog['current_question']}")
                    print(f"     ⏰ Last Updated: {prog['last_updated']}")
                    if prog.get("completed_at"):
                        print(f"     ✅ Completed: {prog['completed_at']}")
                    print()
                else:
                    print(f"  👤 User: {user_id[:8]}... - No progress record found")

            # Check Zep data for these users
            print(f"\n🧠 Zep Memory Data for Recent Users:")
            print("-" * 50)

            for user_id in users_found:
                try:
                    # Get user's knowledge graph from Zep (not async)
                    knowledge_graph = zep_service.manager.get_user_knowledge_graph(
                        user_id
                    )

                    if knowledge_graph and "nodes" in knowledge_graph:
                        nodes = knowledge_graph["nodes"]

                        print(f"  👤 User: {user_id[:8]}...")
                        print(f"     🧠 Total nodes in Zep: {len(nodes)}")

                        # Debug: show all node types
                        entity_types = {}
                        for node in nodes:
                            data = node.get("data", {})
                            entity_type = data.get("entity_type", "unknown")
                            entity_types[entity_type] = (
                                entity_types.get(entity_type, 0) + 1
                            )

                        print(f"     🔍 Node types found: {entity_types}")

                        # Show first few nodes for debugging
                        print(f"     🔎 First few nodes:")
                        for i, node in enumerate(nodes[:3]):
                            data = node.get("data", {})
                            print(
                                f"       {i+1}. Type: {data.get('entity_type', 'unknown')}"
                            )
                            print(f"          ID: {data.get('entity_id', 'unknown')}")
                            print(f"          Data keys: {list(data.keys())}")

                        business_nodes = [
                            node
                            for node in nodes
                            if node.get("data", {}).get("entity_type")
                            == "business_profile_question"
                        ]

                        print(f"     📋 Business profile nodes: {len(business_nodes)}")

                        for node in business_nodes[:5]:  # Show first 5
                            data = node.get("data", {})
                            print(
                                f"       • {data.get('entity_id', 'Unknown')}: {data.get('question', 'Unknown')[:40]}..."
                            )
                            print(
                                f"         Answer: {data.get('answer', 'No answer')[:60]}..."
                            )

                        if len(business_nodes) > 5:
                            print(f"       ... and {len(business_nodes) - 5} more")
                    else:
                        print(
                            f"  👤 User: {user_id[:8]}... - No Zep knowledge graph found or empty"
                        )

                    print()

                except Exception as e:
                    print(f"  👤 User: {user_id[:8]}... - Error getting Zep data: {e}")
                    print()

        # Summary statistics
        print("\n📈 Summary:")
        print("-" * 20)

        # Count total responses by status
        all_progress = (
            supabase.client.table("user_questionnaire_progress")
            .select("status")
            .execute()
        )

        if all_progress.data:
            status_counts = {}
            for prog in all_progress.data:
                status = prog["status"]
                status_counts[status] = status_counts.get(status, 0) + 1

            print("Questionnaire Status Distribution:")
            for status, count in status_counts.items():
                print(f"  {status}: {count} users")

        # Count total responses
        total_responses = (
            supabase.client.table("user_questionnaire_responses")
            .select("id", count="exact")
            .execute()
        )

        print(
            f"\nTotal questionnaire responses in database: {total_responses.count or 0}"
        )

    except Exception as e:
        print(f"❌ Error checking questionnaire data: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(check_recent_questionnaire_data())
