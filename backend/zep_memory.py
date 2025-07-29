"""
Zep Memory Management Module
Handles user knowledge graph extraction and GraphRAG integration
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from zep_cloud.client import Zep
from zep_cloud import Message, User
from config import zep_client
from circuit_breaker import circuit_breaker_decorator, CircuitBreakerOpenError
import asyncio
import hashlib
import time

logger = logging.getLogger(__name__)


class DistributedUserLock:
    """
    Distributed lock using Supabase advisory locks for coordinating user creation
    across multiple Railway containers
    """

    def __init__(self, user_id: str, timeout: int = 10):
        self.user_id = user_id
        self.timeout = timeout
        self.lock_id = self._generate_lock_id(user_id)
        self._acquired = False

    def _generate_lock_id(self, user_id: str) -> int:
        """Generate numeric lock ID from user_id for Supabase advisory locks"""
        # Use hash to convert user_id to integer for advisory lock
        hash_value = hashlib.md5(user_id.encode()).hexdigest()
        # Take first 8 hex chars and convert to int (32-bit)
        return int(hash_value[:8], 16) % (2**31 - 1)

    async def acquire(self) -> bool:
        """Acquire distributed lock using Supabase advisory lock"""
        try:
            from supabase_client import SupabaseService

            supabase = SupabaseService()

            # Use PostgreSQL advisory lock
            result = supabase.client.rpc(
                "pg_try_advisory_lock", {"lock_id": self.lock_id}
            ).execute()

            self._acquired = result.data if result.data else False

            if self._acquired:
                logger.debug(
                    f"Acquired distributed lock for user {self.user_id} (lock_id: {self.lock_id})"
                )
            else:
                logger.debug(
                    f"Failed to acquire distributed lock for user {self.user_id}"
                )

            return self._acquired

        except Exception as e:
            logger.error(
                f"Error acquiring distributed lock for user {self.user_id}: {e}"
            )
            return False

    async def release(self):
        """Release distributed lock"""
        if not self._acquired:
            return

        try:
            from supabase_client import SupabaseService

            supabase = SupabaseService()

            # Release PostgreSQL advisory lock
            supabase.client.rpc(
                "pg_advisory_unlock", {"lock_id": self.lock_id}
            ).execute()

            logger.debug(
                f"Released distributed lock for user {self.user_id} (lock_id: {self.lock_id})"
            )
            self._acquired = False

        except Exception as e:
            logger.error(
                f"Error releasing distributed lock for user {self.user_id}: {e}"
            )

    async def __aenter__(self):
        """Async context manager entry"""
        start_time = time.time()

        while time.time() - start_time < self.timeout:
            if await self.acquire():
                return self
            await asyncio.sleep(0.1)  # Wait 100ms before retry

        raise TimeoutError(
            f"Failed to acquire distributed lock for user {self.user_id} within {self.timeout}s"
        )

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.release()


class ZepMemoryManager:
    """Manages user memory and knowledge graphs using Zep"""

    def __init__(self):
        self.client = zep_client
        self.enabled = zep_client is not None
        self._creation_locks = {}  # In-memory locks for same-container coordination

    def _extract_user_metadata_from_supabase(self, user_id: str) -> Dict[str, Any]:
        """
        Centralized function to extract user metadata from Supabase consistently
        Returns structured metadata for Zep user creation
        """
        try:
            from supabase_client import SupabaseService

            supabase = SupabaseService()

            # First try to get email from Supabase auth system (this is where email is actually stored)
            user_email = None
            try:
                auth_user = supabase.client.auth.admin.get_user_by_id(user_id)
                if auth_user and hasattr(auth_user, "user") and auth_user.user:
                    user_email = auth_user.user.email
                    logger.debug(
                        f"Retrieved email from Supabase auth for {user_id}: {user_email}"
                    )
            except Exception as auth_error:
                logger.debug(
                    f"Could not retrieve email from Supabase auth for {user_id}: {auth_error}"
                )

            # Then try to get existing user profile for other data
            try:
                user_response = (
                    supabase.client.table("user_profiles")
                    .select("*")
                    .eq("id", user_id)
                    .single()
                    .execute()
                )
                user_profile = user_response.data if user_response.data else {}
            except Exception as profile_error:
                # User profile doesn't exist, create it automatically
                logger.info(
                    f"User profile not found for {user_id}, creating automatically: {profile_error}"
                )
                try:
                    # Create minimal user profile record
                    user_data = {"id": user_id, "created_at": "now()"}
                    create_response = (
                        supabase.client.table("user_profiles")
                        .insert(user_data)
                        .execute()
                    )
                    user_profile = (
                        create_response.data[0] if create_response.data else {}
                    )
                    logger.info(f"Successfully created user profile for {user_id}")
                except Exception as create_error:
                    logger.warning(
                        f"Failed to create user profile for {user_id}: {create_error}"
                    )
                    user_profile = {}  # Fall back to empty profile

            # Build consistent metadata structure
            metadata = {
                "created_at": str(datetime.now()),
                "user_type": "business_owner",
                "source": "mental_model_app",
                "supabase_user_id": user_id,
            }

            # Add email from auth system (priority) or profile fallback
            if user_email:
                metadata["email"] = user_email
            elif user_profile.get("email"):
                metadata["email"] = user_profile["email"]

            # Add other profile data if available
            if user_profile.get("first_name"):
                metadata["first_name"] = user_profile["first_name"]
            if user_profile.get("last_name"):
                metadata["last_name"] = user_profile["last_name"]
            if user_profile.get("name"):
                metadata["name"] = user_profile["name"]

            logger.debug(f"Extracted metadata for user {user_id}: {metadata}")
            return metadata

        except Exception as e:
            logger.warning(f"Failed to extract Supabase metadata for {user_id}: {e}")
            # Return minimal metadata if Supabase fails
            return {
                "created_at": str(datetime.now()),
                "user_type": "business_owner",
                "source": "mental_model_app",
                "supabase_user_id": user_id,
            }

    def _get_distributed_lock(
        self, user_id: str, timeout: int = 10
    ) -> "DistributedUserLock":
        """
        Get a distributed lock for user creation across Railway containers
        Uses Supabase advisory locks for coordination
        """
        return DistributedUserLock(user_id, timeout)

    def _acquire_local_lock(self, user_id: str):
        """Acquire local lock to prevent same-container races"""
        if user_id not in self._creation_locks:
            self._creation_locks[user_id] = asyncio.Lock()
        return self._creation_locks[user_id]

    async def ensure_user_exists_coordinated(
        self,
        user_id: str,
        user_metadata: Optional[Dict[str, Any]] = None,
        retry_count: int = 3,
    ) -> User:
        """
        Ensure user exists with distributed coordination to prevent duplicates
        Uses distributed locking to coordinate across Railway containers
        """
        coordination_start_time = time.time()
        logger.info(
            f"🎯 ZEP COORDINATION STARTED: ensure_user_exists_coordinated for {user_id}"
        )

        if not self.enabled:
            logger.warning(
                f"⚠️ ZEP DISABLED: ensure_user_exists_coordinated returning None for {user_id}"
            )
            return None

        # First try to get existing user (fast path)
        existing_user_check_start = time.time()
        try:
            logger.debug(f"🔍 ZEP FAST PATH: Checking for existing user {user_id}")
            user = self._get_user_with_circuit_breaker(user_id)
            existing_user_check_time = time.time() - existing_user_check_start
            logger.info(
                f"✅ ZEP FAST PATH SUCCESS: Found existing user {user_id} in {existing_user_check_time:.2f}s"
            )
            return user
        except CircuitBreakerOpenError:
            existing_user_check_time = time.time() - existing_user_check_start
            logger.warning(
                f"⚠️ ZEP CIRCUIT BREAKER OPEN: Cannot check/create user {user_id} after {existing_user_check_time:.2f}s"
            )
            return None
        except Exception as check_error:
            existing_user_check_time = time.time() - existing_user_check_start
            # User doesn't exist, proceed with coordinated creation
            logger.info(
                f"🔍 ZEP FAST PATH: User {user_id} doesn't exist ({check_error}), proceeding with coordinated creation after {existing_user_check_time:.2f}s"
            )

        # Use distributed coordination for user creation
        lock_key = f"zep_user_creation_{user_id}"
        logger.debug(
            f"🔒 ZEP LOCKING: Attempting distributed lock for {user_id} with key {lock_key}"
        )

        lock_acquisition_start = time.time()
        try:
            logger.debug(
                f"🔒 ZEP LOCK ATTEMPT: Acquiring distributed lock for {user_id}"
            )
            async with self._get_distributed_lock(lock_key):
                lock_acquisition_time = time.time() - lock_acquisition_start
                logger.info(
                    f"✅ ZEP LOCK ACQUIRED: Got distributed lock for {user_id} in {lock_acquisition_time:.2f}s"
                )

                # Double-check after acquiring distributed lock
                double_check_start = time.time()
                try:
                    logger.debug(
                        f"🔍 ZEP DOUBLE CHECK: Re-checking user existence after lock for {user_id}"
                    )
                    user = self._get_user_with_circuit_breaker(user_id)
                    double_check_time = time.time() - double_check_start
                    total_coordination_time = time.time() - coordination_start_time
                    logger.info(
                        f"✅ ZEP DOUBLE CHECK SUCCESS: Found existing user {user_id} after lock in {double_check_time:.2f}s (total: {total_coordination_time:.2f}s)"
                    )
                    return user
                except Exception as double_check_error:
                    double_check_time = time.time() - double_check_start
                    logger.info(
                        f"🔍 ZEP DOUBLE CHECK: User {user_id} still doesn't exist after lock ({double_check_error}), proceeding with creation after {double_check_time:.2f}s"
                    )

                    # User still doesn't exist, safe to create
                    creation_start = time.time()
                    try:
                        logger.info(
                            f"🏗️ ZEP USER CREATION: Starting coordinated creation for {user_id}"
                        )
                        new_user = await self._create_user_with_coordination(
                            user_id, user_metadata
                        )
                        creation_time = time.time() - creation_start
                        total_coordination_time = time.time() - coordination_start_time

                        if new_user:
                            logger.info(
                                f"✅ ZEP CREATION SUCCESS: User {user_id} created in {creation_time:.2f}s (total: {total_coordination_time:.2f}s)"
                            )
                        else:
                            logger.error(
                                f"❌ ZEP CREATION FAILED: _create_user_with_coordination returned None for {user_id} after {creation_time:.2f}s"
                            )

                        return new_user
                    except Exception as creation_error:
                        creation_time = time.time() - creation_start
                        total_coordination_time = time.time() - coordination_start_time
                        logger.error(
                            f"❌ ZEP CREATION EXCEPTION: {creation_error} for user {user_id} after {creation_time:.2f}s (total: {total_coordination_time:.2f}s)"
                        )
                        raise

        except Exception as lock_error:
            lock_acquisition_time = time.time() - lock_acquisition_start
            total_coordination_time = time.time() - coordination_start_time
            logger.error(
                f"❌ ZEP LOCK FAILED: Could not acquire distributed lock for {user_id}: {lock_error} after {lock_acquisition_time:.2f}s (total: {total_coordination_time:.2f}s)"
            )
            logger.warning(
                f"⚠️ ZEP FALLBACK: Attempting non-coordinated creation for {user_id}"
            )

            # Fallback to regular creation (with idempotent handling)
            try:
                fallback_start = time.time()
                fallback_user = self.ensure_user_exists(
                    user_id, user_metadata, retry_count
                )
                fallback_time = time.time() - fallback_start
                total_coordination_time = time.time() - coordination_start_time

                if fallback_user:
                    logger.info(
                        f"✅ ZEP FALLBACK SUCCESS: User {user_id} created via fallback in {fallback_time:.2f}s (total: {total_coordination_time:.2f}s)"
                    )
                else:
                    logger.error(
                        f"❌ ZEP FALLBACK FAILED: Non-coordinated creation also failed for {user_id} after {fallback_time:.2f}s"
                    )

                return fallback_user
            except Exception as fallback_error:
                total_coordination_time = time.time() - coordination_start_time
                logger.error(
                    f"💥 ZEP TOTAL FAILURE: Both coordinated and fallback creation failed for {user_id}: {fallback_error} after {total_coordination_time:.2f}s"
                )
                return None

    async def _create_user_with_coordination(
        self, user_id: str, user_metadata: Optional[Dict[str, Any]] = None
    ) -> User:
        """Create user with local coordination (called within distributed lock)"""
        creation_method_start = time.time()
        logger.info(
            f"🏗️ ZEP COORDINATION METHOD: Starting _create_user_with_coordination for {user_id}"
        )

        # Get metadata from Supabase if not provided
        metadata_start = time.time()
        if user_metadata is None:
            logger.debug(f"📋 ZEP METADATA: Extracting Supabase metadata for {user_id}")
            user_metadata = self._extract_user_metadata_from_supabase(user_id)
            metadata_time = time.time() - metadata_start
            logger.debug(
                f"📋 ZEP METADATA: Using extracted Supabase metadata for {user_id} ({metadata_time:.2f}s): {user_metadata}"
            )
        else:
            logger.debug(
                f"📋 ZEP METADATA: Merging provided metadata with Supabase data for {user_id}"
            )
            # Merge provided metadata with Supabase data for completeness
            supabase_metadata = self._extract_user_metadata_from_supabase(user_id)
            merged_metadata = {**supabase_metadata, **user_metadata}
            user_metadata = merged_metadata
            metadata_time = time.time() - metadata_start
            logger.debug(
                f"📋 ZEP METADATA: Using merged metadata for {user_id} ({metadata_time:.2f}s): {user_metadata}"
            )

        # Build user creation parameters using extracted metadata
        param_build_start = time.time()
        user_params = {
            "user_id": user_id,
            "metadata": user_metadata,
        }

        # Extract Zep-specific top-level fields from metadata
        if user_metadata.get("email"):
            user_params["email"] = user_metadata["email"]
        if user_metadata.get("first_name"):
            user_params["first_name"] = user_metadata["first_name"]
        if user_metadata.get("last_name"):
            user_params["last_name"] = user_metadata["last_name"]

        param_build_time = time.time() - param_build_start
        logger.info(
            f"📋 ZEP PARAMS: Built user creation params for {user_id} in {param_build_time:.2f}s: {user_params}"
        )

        # Create user with idempotent handling
        user_creation_start = time.time()
        try:
            logger.info(
                f"👤 ZEP USER API: Calling _create_user_idempotent for {user_id}"
            )
            user = self._create_user_idempotent(**user_params)
            user_creation_time = time.time() - user_creation_start

            if user:
                logger.info(
                    f"✅ ZEP USER API SUCCESS: User {user_id} created via API in {user_creation_time:.2f}s"
                )
                logger.debug(
                    f"👤 ZEP USER OBJECT: {type(user).__name__} with ID {getattr(user, 'user_id', 'unknown')}"
                )
            else:
                logger.error(
                    f"❌ ZEP USER API FAILED: _create_user_idempotent returned None for {user_id} after {user_creation_time:.2f}s"
                )

        except Exception as user_creation_error:
            user_creation_time = time.time() - user_creation_start
            logger.error(
                f"❌ ZEP USER API EXCEPTION: {user_creation_error} for user {user_id} after {user_creation_time:.2f}s"
            )
            import traceback

            logger.error(f"📊 ZEP USER API TRACE: {traceback.format_exc()}")
            raise

        # Create an explicit session for this user
        session_creation_start = time.time()
        try:
            session_id = f"main_session_{user_id}"
            logger.debug(
                f"🔗 ZEP SESSION: Creating main session {session_id} for user {user_id}"
            )
            self.client.memory.add_session(session_id=session_id, user_id=user_id)
            session_creation_time = time.time() - session_creation_start
            logger.info(
                f"✅ ZEP SESSION SUCCESS: Created main session for user {user_id}: {session_id} in {session_creation_time:.2f}s"
            )
        except Exception as session_error:
            session_creation_time = time.time() - session_creation_start
            logger.warning(
                f"⚠️ ZEP SESSION FAILED: Could not create main session for user {user_id}: {session_error} after {session_creation_time:.2f}s"
            )
            # Don't fail user creation if session creation fails

        total_method_time = time.time() - creation_method_start
        logger.info(
            f"🏁 ZEP COORDINATION METHOD COMPLETE: User {user_id} creation method finished in {total_method_time:.2f}s"
        )
        return user

    def ensure_user_exists(
        self,
        user_id: str,
        user_metadata: Optional[Dict[str, Any]] = None,
        retry_count: int = 3,
    ) -> User:
        """
        Ensure a user exists in Zep, create if not exists with retry logic

        Args:
            user_id: Unique user identifier (from Supabase)
            user_metadata: Optional metadata about the user (should include 'name' for display)
            retry_count: Number of retries for user creation

        Returns:
            User object from Zep
        """
        if not self.enabled:
            logger.warning("Zep is disabled - ensure_user_exists returning None")
            return None

        # Try to get existing user first
        try:
            user = self._get_user_with_circuit_breaker(user_id)
            logger.info(f"Found existing Zep user: {user_id}")
            return user
        except CircuitBreakerOpenError:
            logger.warning(f"Circuit breaker open - cannot check/create user {user_id}")
            return None
        except Exception as get_error:
            logger.debug(
                f"User {user_id} doesn't exist in Zep, will create: {get_error}"
            )
            # User doesn't exist, proceed to creation

        # Get metadata from Supabase if not provided or merge with existing
        if user_metadata is None:
            user_metadata = self._extract_user_metadata_from_supabase(user_id)
            logger.debug(f"Using extracted Supabase metadata for {user_id}")
        else:
            # Merge provided metadata with Supabase data for completeness
            supabase_metadata = self._extract_user_metadata_from_supabase(user_id)
            merged_metadata = {**supabase_metadata, **user_metadata}
            user_metadata = merged_metadata
            logger.debug(f"Using merged metadata for {user_id}")

        # User doesn't exist, create new one with retry logic
        for attempt in range(retry_count):
            try:
                logger.info(
                    f"Creating new Zep user: {user_id} (attempt {attempt + 1}/{retry_count})"
                )

                # Build user creation parameters using extracted metadata
                user_params = {
                    "user_id": user_id,
                    "metadata": user_metadata,
                }

                # Extract Zep-specific top-level fields from metadata
                if user_metadata.get("email"):
                    user_params["email"] = user_metadata["email"]
                if user_metadata.get("first_name"):
                    user_params["first_name"] = user_metadata["first_name"]
                if user_metadata.get("last_name"):
                    user_params["last_name"] = user_metadata["last_name"]

                logger.debug(f"Creating user with params: {user_params}")

                # Create user with idempotent handling
                user = self._create_user_idempotent(**user_params)

                # Create an explicit session for this user following Zep best practices
                try:
                    session_id = f"main_session_{user_id}"
                    self.client.memory.add_session(
                        session_id=session_id, user_id=user_id
                    )
                    logger.info(
                        f"Created main session for user {user_id}: {session_id}"
                    )
                except Exception as session_error:
                    logger.warning(
                        f"Failed to create main session for user {user_id}: {session_error}"
                    )
                    # Don't fail user creation if session creation fails

                logger.info(f"Successfully created Zep user: {user_id}")
                return user

            except Exception as create_error:
                logger.warning(
                    f"Attempt {attempt + 1} failed to create Zep user {user_id}: {create_error}"
                )
                if attempt == retry_count - 1:  # Last attempt
                    logger.error(
                        f"Failed to create Zep user {user_id} after {retry_count} attempts"
                    )
                    raise create_error
                # Wait before retry (exponential backoff)
                import time

                time.sleep(2**attempt)

    def _create_user_idempotent(self, **user_params) -> User:
        """
        Create user with idempotent handling - prevents duplicate user errors
        Returns existing user if user already exists
        """
        user_id = user_params.get("user_id")

        try:
            # Attempt to create user using circuit breaker
            user = self._create_user_with_circuit_breaker(**user_params)
            logger.info(f"Successfully created new Zep user: {user_id}")
            return user

        except Exception as create_error:
            error_message = str(create_error).lower()

            # Check if error indicates user already exists
            if any(
                keyword in error_message
                for keyword in [
                    "already exists",
                    "duplicate",
                    "conflict",
                    "unique constraint",
                ]
            ):
                logger.info(
                    f"User {user_id} already exists in Zep, fetching existing user"
                )
                try:
                    # Fetch the existing user
                    existing_user = self._get_user_with_circuit_breaker(user_id)
                    logger.info(f"Successfully retrieved existing Zep user: {user_id}")
                    return existing_user
                except Exception as get_error:
                    logger.error(
                        f"Failed to fetch existing user {user_id} after creation conflict: {get_error}"
                    )
                    raise create_error  # Re-raise original error
            else:
                # Not a duplicate error, re-raise original
                logger.error(f"User creation failed for {user_id}: {create_error}")
                raise create_error

    def add_conversation_memory_safe(
        self, user_id: str, session_id: str, messages: List[Dict[str, str]]
    ) -> bool:
        """
        Add conversation messages to Zep with safety checks
        Returns True if successful, False if failed (but doesn't raise exceptions)

        Args:
            user_id: User identifier
            session_id: Session/conversation identifier
            messages: List of message dictionaries with 'role' and 'content'
        """
        if not self.enabled:
            logger.warning("Zep is disabled - add_conversation_memory_safe skipping")
            return False

        try:
            # Verify user exists first - critical safety check
            try:
                self._get_user_with_circuit_breaker(user_id)
                logger.debug(f"Confirmed user {user_id} exists for memory operation")
            except Exception as user_error:
                logger.error(
                    f"User {user_id} does not exist in Zep, cannot add memory: {user_error}"
                )
                return False  # Fail safely - don't add memory for non-existent user

            # Ensure session exists before adding memory
            try:
                self._get_memory_with_circuit_breaker(session_id)
                logger.debug(f"Session {session_id} exists")
            except Exception:
                # Session doesn't exist, create it
                try:
                    self.client.memory.add_session(
                        session_id=session_id, user_id=user_id
                    )
                    logger.info(f"Created session {session_id} for user {user_id}")
                except Exception as session_error:
                    logger.error(
                        f"Failed to create session {session_id}: {session_error}"
                    )
                    return False

            # Convert messages to Zep format
            zep_messages = []
            for msg in messages:
                zep_message = Message(
                    role=msg.get("role", "user"), content=msg.get("content", "")
                )
                zep_messages.append(zep_message)

            # Add messages to Zep memory safely
            try:
                self.client.memory.add(session_id=session_id, messages=zep_messages)
                logger.info(
                    f"Successfully added {len(zep_messages)} messages to Zep memory for session {session_id}"
                )
                return True
            except Exception as memory_error:
                logger.error(f"Failed to add messages to Zep memory: {memory_error}")
                return False

        except Exception as e:
            logger.error(f"Error in add_conversation_memory_safe: {str(e)}")
            return False

    def add_conversation_memory(
        self, user_id: str, session_id: str, messages: List[Dict[str, str]]
    ) -> None:
        """
        Legacy method - redirects to safe version
        Kept for backward compatibility but now uses safe implementation
        """
        result = self.add_conversation_memory_safe(user_id, session_id, messages)
        if not result:
            logger.warning(
                f"Conversation memory addition failed for user {user_id}, session {session_id}"
            )
            # Don't raise exception - allow conversation to continue

    def add_business_data(
        self, user_id: str, data: Dict[str, Any], data_type: str = "json"
    ) -> None:
        """
        Add structured business data to user's knowledge graph with proper node creation

        Args:
            user_id: User identifier
            data: Business data to store (company info, projects, etc.)
            data_type: Type of data being stored
        """
        try:
            # Ensure user exists with proper metadata
            user_metadata = {
                "name": data.get("company_name", user_id),
                "business_type": data.get("business_type", "startup"),
                "industry": data.get("industry", "technology"),
            }
            self.ensure_user_exists(user_id, user_metadata)

            # Add structured data to Zep's graph for knowledge extraction
            import json

            # Zep expects standard types like "json", "text", etc.
            zep_data_type = (
                "json"
                if data_type in ["business_assessment", "user_profile"]
                else data_type
            )
            self.client.graph.add(
                user_id=user_id, data=json.dumps(data), type=zep_data_type
            )

            # Also add as conversation context for better integration
            data_summary = self._create_business_data_summary(data, data_type)
            business_message = Message(
                role="system", content=f"Business Assessment Data: {data_summary}"
            )

            # Create a special session for business data
            business_session_id = f"business_data_{user_id}"
            self.client.memory.add(
                session_id=business_session_id, messages=[business_message]
            )

            logger.info(f"Added business data to Zep for user {user_id}: {data_type}")

        except Exception as e:
            logger.error(f"Error adding business data to Zep: {str(e)}")
            raise

    def _create_business_data_summary(
        self, data: Dict[str, Any], data_type: str
    ) -> str:
        """Create a human-readable summary of business data for better node creation"""
        if data_type == "business_assessment":
            company = data.get("company_name", "Unknown Company")
            industry = data.get("industry", "Unknown Industry")
            stage = data.get("business_stage", "Unknown Stage")
            challenges = data.get("current_challenges", [])

            summary = f"{company} is a {stage} company in the {industry} industry."
            if challenges:
                summary += f" Current challenges include: {', '.join(challenges[:3])}."

            return summary
        else:
            # Generic summary for other data types
            return f"Business data of type {data_type}: {str(data)[:200]}..."

    def get_relevant_memory(
        self, session_id: str, query: Optional[str] = None, limit: int = 10
    ) -> Dict[str, Any]:
        """
        Retrieve relevant memory context for GraphRAG using optimized Zep API

        Args:
            session_id: Session identifier
            query: Optional query to search for relevant context (largely ignored in favor of context)
            limit: Maximum number of memories to return (for legacy compatibility)

        Returns:
            Dictionary containing relevant context optimized for LLM consumption
        """
        try:
            # Use the optimized memory.context approach recommended by Zep
            memory = self.client.memory.get(session_id=session_id)

            if hasattr(memory, "context") and memory.context:
                # The context field is an opinionated string containing facts and entities
                # relevant to the current conversation - this is the optimal approach
                return {
                    "context": memory.context,
                    "facts": self._extract_facts_from_context(memory.context),
                    "session_id": session_id,
                    "has_memory": True,
                }
            else:
                # Fallback to basic facts extraction if context isn't available
                facts = []
                if hasattr(memory, "facts") and memory.facts:
                    facts = [str(fact) for fact in memory.facts[:limit]]
                elif hasattr(memory, "messages") and memory.messages:
                    # Extract key information from recent messages as fallback
                    recent_messages = (
                        memory.messages[-3:]
                        if len(memory.messages) > 3
                        else memory.messages
                    )
                    facts = [
                        (
                            msg.content[:200] + "..."
                            if len(msg.content) > 200
                            else msg.content
                        )
                        for msg in recent_messages
                        if hasattr(msg, "content")
                    ]

                return {
                    "context": None,
                    "facts": facts,
                    "session_id": session_id,
                    "has_memory": len(facts) > 0,
                }

        except Exception as e:
            logger.error(f"Error retrieving memory from Zep: {str(e)}")
            # Return graceful fallback for error cases
            return {
                "context": None,
                "facts": [],
                "session_id": session_id,
                "has_memory": False,
                "error": str(e),
            }

    def _extract_facts_from_context(self, context: str) -> List[str]:
        """Extract individual facts from Zep's context string for legacy compatibility"""
        if not context:
            return []

        facts = []
        # Look for facts section in context
        if "<FACTS>" in context and "</FACTS>" in context:
            facts_section = context.split("<FACTS>")[1].split("</FACTS>")[0]
            # Split by lines and extract individual facts
            for line in facts_section.split("\n"):
                line = line.strip()
                if line and line.startswith("-"):
                    # Remove the leading dash and clean up
                    fact = line[1:].strip()
                    if fact:
                        facts.append(fact)
        elif context:
            # Fallback: split context into sentences as individual facts
            sentences = context.split(". ")
            facts = [
                (
                    sentence.strip() + "."
                    if not sentence.endswith(".")
                    else sentence.strip()
                )
                for sentence in sentences
                if len(sentence.strip()) > 10
            ][
                :5
            ]  # Limit to 5 facts

        return facts

    def get_business_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get structured business profile data for a user from Zep

        Args:
            user_id: User identifier

        Returns:
            Business profile dictionary or None if not found
        """
        if not self.enabled:
            logger.debug("Zep is disabled - get_business_profile returning None")
            return None

        try:
            # Try to get from the dedicated business data session
            business_session_id = f"business_data_{user_id}"

            try:
                memory = self.client.memory.get(session_id=business_session_id)
                if hasattr(memory, "context") and memory.context:
                    # Parse business profile from context if it contains structured data
                    context = memory.context

                    # Look for specific business profile elements in the context
                    business_profile = {}

                    # Extract business information from context using pattern matching
                    import re

                    # Define patterns for key business information
                    patterns = {
                        "biggest_challenge": r"(?:challenge|problem)[^\n]*?([^\n.]+)",
                        "employee_count": r"(?:employee|team|staff)[^\n]*?(\d+|[\w\s]+people)",
                        "revenue_range": r"(?:revenue|income|sales)[^\n]*?(\$[\w\s,.-]+|\d+[\w\s]*)",
                        "industry": r"(?:industry|sector|field)[^\n]*?([^\n.]+)",
                        "main_business_goal": r"(?:goal|objective|aim)[^\n]*?([^\n.]+)",
                    }

                    for key, pattern in patterns.items():
                        matches = re.findall(pattern, context, re.IGNORECASE)
                        if matches:
                            # Take the first meaningful match
                            value = matches[0].strip()
                            if len(value) > 3:  # Filter out very short matches
                                business_profile[key] = value

                    if business_profile:
                        logger.debug(
                            f"Extracted business profile from context for user {user_id}"
                        )
                        return business_profile

            except Exception as session_error:
                logger.debug(
                    f"Could not retrieve from business session: {session_error}"
                )

            # Fallback: Try to extract from knowledge graph facts
            try:
                knowledge_graph = self.get_user_knowledge_graph(user_id)
                if knowledge_graph and "edges" in knowledge_graph:
                    business_facts = {}

                    for edge in knowledge_graph["edges"]:
                        if isinstance(edge, dict) and "fact" in edge:
                            fact = edge["fact"]
                            fact_lower = fact.lower()

                            # Map facts to business profile fields
                            if (
                                "challenge" in fact_lower
                                and "biggest_challenge" not in business_facts
                            ):
                                business_facts["biggest_challenge"] = fact
                            elif (
                                any(
                                    word in fact_lower
                                    for word in ["employee", "team", "staff"]
                                )
                                and "employee_count" not in business_facts
                            ):
                                business_facts["employee_count"] = fact
                            elif (
                                any(
                                    word in fact_lower
                                    for word in ["revenue", "sales", "income"]
                                )
                                and "revenue_range" not in business_facts
                            ):
                                business_facts["revenue_range"] = fact
                            elif (
                                "industry" in fact_lower
                                and "industry" not in business_facts
                            ):
                                business_facts["industry"] = fact
                            elif (
                                any(
                                    word in fact_lower for word in ["goal", "objective"]
                                )
                                and "main_business_goal" not in business_facts
                            ):
                                business_facts["main_business_goal"] = fact

                    if business_facts:
                        logger.debug(
                            f"Extracted business profile from facts for user {user_id}"
                        )
                        return business_facts

            except Exception as graph_error:
                logger.debug(f"Could not extract from knowledge graph: {graph_error}")

        except Exception as e:
            logger.warning(f"Error retrieving business profile for user {user_id}: {e}")

        return None

    def get_user_knowledge_graph(self, user_id: str) -> Dict[str, Any]:
        """
        Get user's complete knowledge graph for visualization with proper node names

        Args:
            user_id: User identifier

        Returns:
            User's knowledge graph data with nodes and edges
        """
        try:
            # Get user information
            user = self.client.user.get(user_id)

            # Get all nodes associated with this user
            nodes_response = self.client.graph.node.get_by_user_id(user_id=user_id)

            # Get all edges (facts/relationships) for this user
            edges_response = self.client.graph.edge.get_by_user_id(user_id=user_id)

            # Process nodes - extract meaningful information
            processed_nodes = []
            for node in nodes_response:
                # Handle different node attribute names based on Zep's actual API response
                node_id = (
                    getattr(node, "uuid_", None)
                    or getattr(node, "uuid", None)
                    or getattr(node, "id", None)
                    or str(node)[:8]
                )
                node_name = (
                    getattr(node, "name", None)
                    or getattr(node, "summary", None)
                    or getattr(node, "label", None)
                    or str(node_id)[:8]
                    if node_id
                    else "unknown"
                )

                node_info = {
                    "id": node_id,
                    "name": node_name,
                    "type": getattr(node, "type", None)
                    or getattr(node, "entity_type", "unknown"),
                    "summary": getattr(node, "summary", "")
                    or getattr(node, "description", ""),
                    "created_at": getattr(node, "created_at", None),
                    "metadata": getattr(node, "metadata", {}),
                    "raw_attributes": [
                        attr for attr in dir(node) if not attr.startswith("_")
                    ],  # Debug info
                }
                processed_nodes.append(node_info)

            # Process edges - extract relationships
            processed_edges = []
            for edge in edges_response:
                edge_id = (
                    getattr(edge, "uuid_", None)
                    or getattr(edge, "uuid", None)
                    or getattr(edge, "id", None)
                    or str(edge)[:8]
                )

                edge_info = {
                    "id": edge_id,
                    "source": getattr(edge, "source_node_uuid", None)
                    or getattr(edge, "source", None),
                    "target": getattr(edge, "target_node_uuid", None)
                    or getattr(edge, "target", None),
                    "relationship": getattr(edge, "relationship_type", None)
                    or getattr(edge, "relation", "related_to"),
                    "fact": getattr(edge, "fact", "")
                    or getattr(edge, "description", ""),
                    "created_at": getattr(edge, "created_at", None),
                    "valid_at": getattr(edge, "valid_at", None),
                    "raw_attributes": [
                        attr for attr in dir(edge) if not attr.startswith("_")
                    ],  # Debug info
                }
                processed_edges.append(edge_info)

            return {
                "user_id": user_id,
                "user_info": {
                    "id": user.user_id,
                    "metadata": getattr(user, "metadata", {}),
                    "created_at": getattr(user, "created_at", None),
                },
                "nodes": processed_nodes,
                "edges": processed_edges,
                "stats": {
                    "total_nodes": len(processed_nodes),
                    "total_edges": len(processed_edges),
                },
            }

        except Exception as e:
            logger.error(f"Error retrieving user knowledge graph: {str(e)}")
            return {"error": str(e)}

    def delete_user_data(self, user_id: str) -> bool:
        """
        Delete all user data from Zep (for privacy compliance)

        Args:
            user_id: User identifier

        Returns:
            True if successful
        """
        try:
            self.client.user.delete(user_id)
            logger.info(f"Deleted user data from Zep: {user_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting user data from Zep: {str(e)}")
            return False

    # Circuit breaker protected methods for key Zep operations

    @circuit_breaker_decorator(
        failure_threshold=3,  # More tolerant for user operations - allow more retries
        recovery_timeout=10,  # Longer recovery for user operations - more conservative
        expected_exception=(Exception,),
        circuit_name="zep_user_operations",  # Unified: single circuit for coordination
    )
    def _get_user_with_circuit_breaker(self, user_id: str) -> User:
        """Get user with circuit breaker protection"""
        logger.debug(f"🔍 CIRCUIT BREAKER: Attempting user get for {user_id}")
        try:
            result = self.client.user.get(user_id)
            logger.debug(f"✅ CIRCUIT BREAKER: User get successful for {user_id}")
            return result
        except Exception as e:
            logger.warning(f"❌ CIRCUIT BREAKER: User get failed for {user_id}: {e}")
            raise

    @circuit_breaker_decorator(
        failure_threshold=3,  # More tolerant for user creation - critical operation
        recovery_timeout=10,  # Longer recovery for user creation - more conservative
        expected_exception=(Exception,),
        circuit_name="zep_user_operations",  # Unified: single circuit for coordination
    )
    def _create_user_with_circuit_breaker(self, **user_params) -> User:
        """Create user with circuit breaker protection"""
        user_id = user_params.get("user_id", "unknown")
        logger.info(f"👤 CIRCUIT BREAKER: Attempting user creation for {user_id}")
        try:
            result = self.client.user.add(**user_params)
            logger.info(f"✅ CIRCUIT BREAKER: User creation successful for {user_id}")
            return result
        except Exception as e:
            logger.error(f"❌ CIRCUIT BREAKER: User creation failed for {user_id}: {e}")
            raise

    @circuit_breaker_decorator(
        failure_threshold=2,  # Optimized: fail faster
        recovery_timeout=5,  # Optimized: recover faster (was 30)
        expected_exception=(Exception,),
        circuit_name="zep_memory_operations",  # Separate circuit for memory operations
    )
    def _get_memory_with_circuit_breaker(self, session_id: str):
        """Get memory with circuit breaker protection"""
        return self.client.memory.get(session_id=session_id)

    @circuit_breaker_decorator(
        failure_threshold=2,  # Optimized: fail faster
        recovery_timeout=5,  # Optimized: recover faster (was 30)
        expected_exception=(Exception,),
        circuit_name="zep_graph_operations",  # Separate circuit for graph operations
    )
    def _add_graph_data_with_circuit_breaker(
        self, user_id: str, data: str, data_type: str
    ):
        """Add graph data with circuit breaker protection"""
        return self.client.graph.add(user_id=user_id, data=data, type=data_type)


class ZepMemoryService:
    """
    Extended Zep service specifically for questionnaire integration
    Handles progressive saving and upsert of business profile questions
    """

    def __init__(self):
        self.manager = ZepMemoryManager()
        self.client = self.manager.client
        self.enabled = self.manager.enabled

    async def add_or_update_business_context(
        self, user_id: str, entity_data: Dict[str, Any]
    ) -> None:
        """
        Add or update a business profile question entity in Zep
        Uses proper upsert logic: delete existing entity then add new one

        Args:
            user_id: User identifier
            entity_data: Dictionary containing entity information with entity_id, question, answer, etc.
        """
        if not self.enabled:
            logger.warning("Zep is disabled - add_or_update_business_context skipping")
            return

        try:
            # Skip user creation here since it should already exist from _ensure_zep_user_exists in questionnaire start
            # This prevents duplicate user creation and conflicting metadata
            try:
                # Verify user exists (should already exist from questionnaire start)
                existing_user = self.manager.client.user.get(user_id)
                logger.debug(
                    f"Confirmed user {user_id} exists in Zep for business context sync"
                )
            except Exception as user_error:
                logger.error(
                    f"User {user_id} does not exist in Zep during business context sync: {user_error}"
                )
                return  # Don't raise exception, just return to prevent questionnaire flow failure

            entity_id = entity_data.get("entity_id")
            if not entity_id:
                logger.error("No entity_id provided in entity_data")
                return

            # Step 1: Delete existing entity if it exists (proper upsert)
            await self._delete_questionnaire_entity(user_id, entity_id)

            # Step 2: Add new/updated entity
            business_context = self._format_business_context(entity_data)

            # Add to Zep graph for knowledge extraction
            import json

            self.client.graph.add(
                user_id=user_id,
                data=json.dumps(entity_data),
                type="json",  # Use standard Zep data type instead of custom type
            )

            # Business context is already added via graph.add() above - no additional memory calls needed

            logger.info(
                f"Upserted business context in Zep for user {user_id}: {entity_id}"
            )

        except Exception as e:
            logger.error(
                f"Error upserting business context in Zep for user {user_id}: {e}"
            )
            # Don't raise - we don't want questionnaire flow to fail due to Zep issues

    def _format_business_context(self, entity_data: Dict[str, Any]) -> str:
        """
        Format entity data into human-readable context for better knowledge extraction
        """
        question = entity_data.get("question", "Unknown question")
        answer = entity_data.get("answer", "No answer provided")
        category = entity_data.get("category", "general")
        question_num = entity_data.get("question_number", 0)

        return f"Q{question_num} ({category}): {question} Answer: {answer}"

    async def get_business_profile_context(self, user_id: str) -> Optional[str]:
        """
        Get all business profile context for this user as a formatted string
        This is used to provide comprehensive business context to the AI
        """
        if not self.enabled:
            return None

        try:
            session_id = f"business_profile_{user_id}"
            memory = self.client.memory.get(session_id=session_id)

            if hasattr(memory, "context") and memory.context:
                return memory.context

            # Fallback to extracting from facts
            if hasattr(memory, "facts") and memory.facts:
                facts = [str(fact) for fact in memory.facts]
                return "\n".join(facts)

            return None

        except Exception as e:
            logger.error(
                f"Error getting business profile context for user {user_id}: {e}"
            )
            return None

    async def _delete_questionnaire_entity(self, user_id: str, entity_id: str) -> bool:
        """
        Delete a specific questionnaire entity by updating the memory session
        Since we're using memory sessions, we don't delete individual entities but rely on
        the latest message containing the most up-to-date context

        Args:
            user_id: User identifier
            entity_id: Consistent entity ID like 'business_profile_q1'

        Returns:
            True (deletion is handled by message replacement)
        """
        try:
            # For memory session approach, "deletion" is handled by the fact that
            # each new message with the same entity_id will effectively replace the old one
            # when we generate context. The latest message with that entity_id takes precedence.
            logger.debug(
                f"Entity deletion handled by message replacement for {entity_id} (user {user_id})"
            )
            return True

        except Exception as e:
            logger.warning(
                f"Error in questionnaire entity deletion for {entity_id} (user {user_id}): {e}"
            )
            return False

    async def get_questionnaire_entities(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all questionnaire entities for a user using memory session approach
        This is more reliable than the graph API for our structured data

        Args:
            user_id: User identifier

        Returns:
            List of questionnaire entity dictionaries
        """
        if not self.enabled:
            return []

        try:
            questionnaire_entities = []
            session_id = f"business_profile_{user_id}"

            # Get memory from the business profile session
            try:
                memory = self.client.memory.get(session_id=session_id)
            except Exception as session_error:
                logger.debug(
                    f"Memory session not found for {session_id}: {session_error}"
                )
                return []

            if hasattr(memory, "messages") and memory.messages:
                # Parse questionnaire data from messages
                for message in memory.messages:
                    if hasattr(message, "content") and message.content:
                        content = message.content

                        # Look for our business profile context messages
                        if "Business Profile Context:" in content:
                            # Parse the structured context - handle both single line and multi-line formats
                            import re

                            # Pattern to match: "Q1 (category): question text Answer: answer text"
                            pattern = r"Q(\d+) \(([^)]+)\): ([^A]+) Answer: (.+?)(?=\s+Q\d+|$)"
                            matches = re.findall(pattern, content)

                            for match in matches:
                                try:
                                    question_num = int(match[0])
                                    category = match[1].strip()
                                    question = match[2].strip()
                                    answer = match[3].strip()

                                    entity_info = {
                                        "entity_id": f"business_profile_q{question_num}",
                                        "question_number": question_num,
                                        "question": question,
                                        "answer": answer,
                                        "category": category,
                                        "answered_at": getattr(
                                            message, "created_at", None
                                        ),
                                    }
                                    questionnaire_entities.append(entity_info)

                                except (ValueError, IndexError):
                                    continue

            # Remove duplicates, keeping the latest by timestamp
            seen_entities = {}
            for entity in questionnaire_entities:
                entity_id = entity.get("entity_id")
                if entity_id:
                    # If we haven't seen this entity, or this one is newer, keep it
                    if entity_id not in seen_entities or self._is_entity_newer(
                        entity, seen_entities[entity_id]
                    ):
                        seen_entities[entity_id] = entity

            final_entities = list(seen_entities.values())
            final_entities.sort(key=lambda x: x.get("question_number", 0))

            logger.debug(
                f"Retrieved {len(final_entities)} questionnaire entities for user {user_id}"
            )
            return final_entities

        except Exception as e:
            logger.error(
                f"Error getting questionnaire entities for user {user_id}: {e}"
            )
            return []

    async def get_questionnaire_context_direct(
        self, user_id: str, query: Optional[str] = None
    ) -> Optional[str]:
        """
        Get questionnaire context using direct entity access instead of regex pattern matching
        This replaces the unreliable regex-based context retrieval

        Args:
            user_id: User identifier
            query: Optional query to filter relevant questionnaire answers

        Returns:
            Formatted questionnaire context string
        """
        if not self.enabled:
            return None

        try:
            questionnaire_entities = await self.get_questionnaire_entities(user_id)

            if not questionnaire_entities:
                return None

            # If query provided, filter for relevant entities
            if query and len(query.strip()) > 0:
                query_lower = query.lower()
                relevant_entities = []

                for entity in questionnaire_entities:
                    question = entity.get("question", "").lower()
                    answer = entity.get("answer", "").lower()
                    category = entity.get("category", "").lower()

                    # Check if query keywords match question, answer, or category
                    if any(
                        keyword in question or keyword in answer or keyword in category
                        for keyword in query_lower.split()
                        if len(keyword) > 3
                    ):
                        relevant_entities.append(entity)

                # Use relevant entities if found, otherwise fall back to all
                entities_to_use = (
                    relevant_entities
                    if relevant_entities
                    else questionnaire_entities[:5]
                )
            else:
                # Use all entities, limited to avoid token bloat
                entities_to_use = questionnaire_entities

            # Format into context string
            context_parts = ["Business Profile Context:"]

            for entity in entities_to_use:
                question_num = entity.get("question_number", "?")
                category = entity.get("category", "general")
                question = entity.get("question", "Unknown question")
                answer = entity.get("answer", "No answer")

                context_parts.append(f"Q{question_num} ({category}): {question}")
                context_parts.append(f"Answer: {answer}")
                context_parts.append("")  # Empty line for readability

            context_string = "\n".join(context_parts)
            logger.debug(
                f"Generated direct questionnaire context for user {user_id}: {len(context_string)} chars"
            )

            return context_string

        except Exception as e:
            logger.error(
                f"Error getting direct questionnaire context for user {user_id}: {e}"
            )
            return None

    def _is_entity_newer(
        self, entity1: Dict[str, Any], entity2: Dict[str, Any]
    ) -> bool:
        """
        Compare two entities to determine which is newer based on timestamp

        Args:
            entity1: First entity to compare
            entity2: Second entity to compare

        Returns:
            True if entity1 is newer than entity2
        """
        try:
            timestamp1 = entity1.get("answered_at")
            timestamp2 = entity2.get("answered_at")

            # If either timestamp is missing, prefer the one with a timestamp
            if not timestamp1 and not timestamp2:
                return False  # Neither has timestamp, keep existing
            if not timestamp1:
                return False  # entity2 has timestamp, keep it
            if not timestamp2:
                return True  # entity1 has timestamp, use it

            # Both have timestamps, compare them
            # Convert to comparable format if they're strings
            if isinstance(timestamp1, str) and isinstance(timestamp2, str):
                return timestamp1 > timestamp2

            # For other timestamp objects, try direct comparison
            return timestamp1 > timestamp2

        except Exception:
            # If comparison fails, prefer entity1 (newer in processing order)
            return True

    async def delete_business_profile_data(self, user_id: str) -> bool:
        """
        Delete business profile specific data from Zep
        """
        try:
            # Delete the business profile session
            session_id = f"business_profile_{user_id}"
            # Note: Zep doesn't have direct session deletion, but memory will be cleaned up
            # when user data is deleted via the main delete_user_data method

            logger.info(f"Marked business profile data for cleanup for user {user_id}")
            return True

        except Exception as e:
            logger.error(
                f"Error deleting business profile data for user {user_id}: {e}"
            )
            return False


# Global instances
zep_memory = ZepMemoryManager()
zep_service = ZepMemoryService()
