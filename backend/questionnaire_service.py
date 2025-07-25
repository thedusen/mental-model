"""
Questionnaire Service for Chat-Integrated Business Profile Collection
"""

import os
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from supabase_client import SupabaseService
from zep_memory import zep_service

logger = logging.getLogger(__name__)


class QuestionnaireService:
    """Service for managing the chat-integrated questionnaire flow"""

    def __init__(self):
        self.supabase = SupabaseService()
        self.zep = zep_service

    async def start_questionnaire(self, user_id: str) -> Dict:
        """
        Initialize questionnaire session for user
        Returns first question and creates progress record
        """
        try:
            # Create or update progress record
            await self._create_or_update_progress(
                user_id=user_id,
                status="in_progress",
                current_question=1,
                started_at=datetime.now().isoformat(),
            )

            # Get first question
            first_question = await self._get_question_by_number(1)
            if not first_question:
                raise Exception("First question not found")

            return {
                "question": first_question,
                "progress": {"current": 1, "total": 11, "status": "in_progress"},
                "message": f"Let's start with your business profile. {first_question['question_text']}",
            }

        except Exception as e:
            print(f"Error starting questionnaire for user {user_id}: {e}")
            raise

    async def get_current_question(self, user_id: str) -> Optional[Dict]:
        """
        Get current question and progress for user
        """
        try:
            progress = await self._get_progress(user_id)
            if not progress:
                return None

            if progress["status"] == "completed":
                return {
                    "completed": True,
                    "message": "You've already completed the business profile questionnaire!",
                }

            current_q_num = progress.get("current_question", 1)
            question = await self._get_question_by_number(current_q_num)

            if not question:
                return None

            return {
                "question": question,
                "progress": {
                    "current": current_q_num,
                    "total": 11,
                    "status": progress["status"],
                },
            }

        except Exception as e:
            print(f"Error getting current question for user {user_id}: {e}")
            return None

    async def submit_answer(
        self, user_id: str, question_id: int, answer_text: str
    ) -> Dict:
        """
        Submit answer for a question, save to DB and Zep, return next question
        """
        try:
            # Validate question exists
            question = await self._get_question_by_id(question_id)
            if not question:
                raise Exception(f"Question {question_id} not found")

            # Save response to database
            await self._save_response(user_id, question_id, answer_text)

            # Immediately sync to Zep for progressive context building
            zep_sync_success = await self._sync_answer_to_zep(
                user_id, question, answer_text
            )
            if not zep_sync_success:
                logger.warning(
                    f"Failed to sync answer to Zep for user {user_id}, question {question_id} - continuing with questionnaire"
                )

            # Check if questionnaire is complete
            answered_count = await self._count_answered_questions(user_id)

            if answered_count >= 11:
                # Mark as completed
                await self._create_or_update_progress(
                    user_id=user_id,
                    status="completed",
                    current_question=11,
                    completed_at=datetime.now().isoformat(),
                )
                return {
                    "completed": True,
                    "message": "Thank you! You've completed the business profile questionnaire. This information will help me provide more personalized assistance.",
                    "progress": {"current": 11, "total": 11, "status": "completed"},
                }

            # Get next question
            next_question_num = question["question_number"] + 1
            next_question = await self._get_question_by_number(next_question_num)

            if not next_question:
                # This shouldn't happen with our 11 questions, but handle gracefully
                return {
                    "completed": True,
                    "message": "Thank you for completing the questionnaire!",
                    "progress": {"current": 11, "total": 11, "status": "completed"},
                }

            # Update progress to next question
            await self._create_or_update_progress(
                user_id=user_id,
                status="in_progress",
                current_question=next_question_num,
            )

            return {
                "question": next_question,
                "progress": {
                    "current": next_question_num,
                    "total": 11,
                    "status": "in_progress",
                },
                "message": f"Great! Next question: {next_question['question_text']}",
            }

        except Exception as e:
            print(
                f"Error submitting answer for user {user_id}, question {question_id}: {e}"
            )
            raise

    async def handle_command(self, user_id: str, command: str) -> Dict:
        """
        Handle special commands: skip, pause, previous
        """
        try:
            progress = await self._get_progress(user_id)
            if not progress:
                return {"error": "No active questionnaire found"}

            current_q_num = progress.get("current_question", 1)

            if command.lower() == "skip":
                # Get the actual question to use its database ID
                current_question = await self._get_question_by_number(current_q_num)
                if not current_question:
                    return {"error": f"Question {current_q_num} not found"}

                # Mark current question as skipped using the correct question_id
                await self._save_response(
                    user_id, current_question["id"], "", skipped=True
                )

                # Move to next question
                if current_q_num >= 11:
                    await self._create_or_update_progress(
                        user_id=user_id,
                        status="completed",
                        completed_at=datetime.now().isoformat(),
                    )
                    return {
                        "completed": True,
                        "message": "Questionnaire completed! You can always edit your answers later.",
                        "progress": {"current": 11, "total": 11, "status": "completed"},
                    }

                next_question = await self._get_question_by_number(current_q_num + 1)
                await self._create_or_update_progress(
                    user_id=user_id, current_question=current_q_num + 1
                )

                return {
                    "question": next_question,
                    "progress": {
                        "current": current_q_num + 1,
                        "total": 11,
                        "status": "in_progress",
                    },
                    "message": f"Skipped. Next question: {next_question['question_text']}",
                }

            elif command.lower() == "pause":
                await self._create_or_update_progress(user_id=user_id, status="paused")
                return {
                    "paused": True,
                    "message": "Questionnaire paused. You can resume anytime by typing 'resume' or clicking the reminder.",
                    "progress": {
                        "current": current_q_num,
                        "total": 11,
                        "status": "paused",
                    },
                }

            elif command.lower() == "previous":
                if current_q_num <= 1:
                    return {
                        "error": "Already at the first question",
                        "progress": {
                            "current": current_q_num,
                            "total": 11,
                            "status": progress["status"],
                        },
                    }

                prev_question = await self._get_question_by_number(current_q_num - 1)
                await self._create_or_update_progress(
                    user_id=user_id, current_question=current_q_num - 1
                )

                return {
                    "question": prev_question,
                    "progress": {
                        "current": current_q_num - 1,
                        "total": 11,
                        "status": "in_progress",
                    },
                    "message": f"Going back. {prev_question['question_text']}",
                }

            elif command.lower() == "resume":
                if progress["status"] != "paused":
                    return {"error": "No paused questionnaire to resume"}

                await self._create_or_update_progress(
                    user_id=user_id, status="in_progress"
                )

                current_question = await self._get_question_by_number(current_q_num)
                return {
                    "question": current_question,
                    "progress": {
                        "current": current_q_num,
                        "total": 11,
                        "status": "in_progress",
                    },
                    "message": f"Resuming questionnaire. {current_question['question_text']}",
                }

            else:
                return {"error": f"Unknown command: {command}"}

        except Exception as e:
            print(f"Error handling command '{command}' for user {user_id}: {e}")
            raise

    async def get_all_responses(self, user_id: str) -> List[Dict]:
        """
        Get all user responses for edit form
        """
        try:
            response = (
                self.supabase.client.table("user_questionnaire_responses")
                .select("*, questionnaire_questions(question_text, question_category)")
                .eq("user_id", user_id)
                .order("question_id")
                .execute()
            )
            return response.data

        except Exception as e:
            print(f"Error getting all responses for user {user_id}: {e}")
            return []

    async def update_response(
        self, user_id: str, question_id: int, new_answer: str
    ) -> bool:
        """
        Update a specific question response and sync to Zep
        """
        try:
            # Update in database
            await self._save_response(user_id, question_id, new_answer)

            # Get question details and sync to Zep
            question = await self._get_question_by_id(question_id)
            if question:
                await self._sync_answer_to_zep(user_id, question, new_answer)

            return True

        except Exception as e:
            print(
                f"Error updating response for user {user_id}, question {question_id}: {e}"
            )
            return False

    # Private helper methods

    async def _get_question_by_number(self, question_number: int) -> Optional[Dict]:
        """Get question by question_number"""
        try:
            response = (
                self.supabase.client.table("questionnaire_questions")
                .select("*")
                .eq("question_number", question_number)
                .single()
                .execute()
            )
            return response.data
        except Exception:
            return None

    async def _get_question_by_id(self, question_id: int) -> Optional[Dict]:
        """Get question by id"""
        try:
            response = (
                self.supabase.client.table("questionnaire_questions")
                .select("*")
                .eq("id", question_id)
                .single()
                .execute()
            )
            return response.data
        except Exception:
            return None

    async def _get_progress(self, user_id: str) -> Optional[Dict]:
        """Get user's questionnaire progress"""
        try:
            response = (
                self.supabase.client.table("user_questionnaire_progress")
                .select("*")
                .eq("user_id", user_id)
                .single()
                .execute()
            )
            return response.data
        except Exception:
            return None

    async def _create_or_update_progress(self, user_id: str, **updates) -> None:
        """Create or update progress record"""
        updates["user_id"] = user_id
        updates["last_updated"] = datetime.now().isoformat()

        self.supabase.client.table("user_questionnaire_progress").upsert(
            updates, on_conflict="user_id"
        ).execute()

    async def _save_response(
        self, user_id: str, question_id: int, response_text: str, skipped: bool = False
    ) -> None:
        """Save response to database"""
        data = {
            "user_id": user_id,
            "question_id": question_id,
            "response_text": response_text,
            "skipped": skipped,
        }

        self.supabase.client.table("user_questionnaire_responses").upsert(
            data, on_conflict="user_id,question_id"
        ).execute()

    async def _count_answered_questions(self, user_id: str) -> int:
        """Count non-skipped answered questions for user"""
        try:
            response = (
                self.supabase.client.table("user_questionnaire_responses")
                .select("id", count="exact")
                .eq("user_id", user_id)
                .neq("response_text", "")
                .eq("skipped", False)
                .execute()
            )
            return response.count or 0
        except Exception:
            return 0

    async def _sync_answer_to_zep(
        self, user_id: str, question: Dict, answer: str
    ) -> bool:
        """
        Sync individual answer to Zep with consistent entity ID and enhanced error handling
        This allows for progressive context building and easy updates

        Returns:
            bool: True if sync was successful, False otherwise
        """
        try:
            if not answer or answer.strip() == "":
                return True  # Empty answers are "successfully" skipped

            # Get user profile from Supabase to provide better user metadata to Zep
            user_profile = None
            try:
                user_response = (
                    self.supabase.client.table("user_profiles")
                    .select("*")
                    .eq("user_id", user_id)
                    .single()
                    .execute()
                )
                user_profile = user_response.data if user_response.data else None
            except Exception as profile_error:
                logger.debug(
                    f"Could not get user profile for {user_id}: {profile_error}"
                )

            # Ensure user exists in Zep with enhanced metadata
            user_metadata = {
                "user_type": "business_owner",
                "source": "questionnaire",
            }

            if user_profile:
                if user_profile.get("email"):
                    user_metadata["email"] = user_profile["email"]
                if user_profile.get("first_name"):
                    user_metadata["first_name"] = user_profile["first_name"]
                if user_profile.get("last_name"):
                    user_metadata["last_name"] = user_profile["last_name"]

            # Ensure user exists with retry logic
            try:
                self.zep.manager.ensure_user_exists(
                    user_id, user_metadata, retry_count=2
                )
            except Exception as user_error:
                logger.error(
                    f"Failed to ensure user exists in Zep for {user_id}: {user_error}"
                )
                return False

            entity_id = f"business_profile_q{question['question_number']}"

            entity_data = {
                "entity_id": entity_id,
                "entity_type": "business_profile_question",
                "question": question["question_text"],
                "answer": answer.strip(),
                "question_number": question["question_number"],
                "category": question.get("question_category", "general"),
                "answered_at": datetime.now().isoformat(),
            }

            # Use Zep's upsert functionality to overwrite existing entities with retry
            retry_count = 2
            for attempt in range(retry_count):
                try:
                    await self.zep.add_or_update_business_context(user_id, entity_data)
                    logger.debug(
                        f"Successfully synced answer to Zep for user {user_id}, question {question['question_number']}"
                    )
                    return True
                except Exception as sync_error:
                    logger.warning(
                        f"Attempt {attempt + 1} failed to sync to Zep for user {user_id}, question {question['question_number']}: {sync_error}"
                    )
                    if attempt == retry_count - 1:
                        logger.error(
                            f"Failed to sync to Zep after {retry_count} attempts"
                        )
                        return False
                    # Brief wait before retry
                    import asyncio

                    await asyncio.sleep(1)

        except Exception as e:
            # Log but don't fail the questionnaire flow if Zep sync fails
            logger.error(
                f"Failed to sync answer to Zep for user {user_id}, question {question['question_number']}: {e}"
            )
            return False

    async def get_questionnaire_status(self, user_id: str) -> Dict:
        """
        Get comprehensive questionnaire status for user
        """
        try:
            progress = await self._get_progress(user_id)

            if not progress:
                return {
                    "status": "not_started",
                    "current_question": 1,
                    "total_questions": 11,
                    "questions_completed": 0,
                    "should_show_nudge": True,
                }

            answered_count = await self._count_answered_questions(user_id)

            return {
                "status": progress["status"],
                "current_question": progress.get("current_question", 1),
                "total_questions": 11,
                "questions_completed": answered_count,
                "started_at": progress.get("started_at"),
                "completed_at": progress.get("completed_at"),
                "should_show_nudge": progress["status"] in ["not_started", "paused"],
            }

        except Exception as e:
            print(f"Error getting questionnaire status for user {user_id}: {e}")
            return {
                "status": "error",
                "current_question": 1,
                "total_questions": 11,
                "questions_completed": 0,
                "should_show_nudge": False,
            }


# Create singleton instance
questionnaire_service = QuestionnaireService()
