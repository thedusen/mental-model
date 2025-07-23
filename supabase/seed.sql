-- Seed data for testing
-- Note: In production, users would be created through the auth flow

-- Insert test user (only for local development)
-- You'll need to create actual auth users through Supabase Studio or the auth API

-- Sample data structure for reference:
-- INSERT INTO auth.users (id, email, encrypted_password, email_confirmed_at, created_at, updated_at)
-- VALUES 
--   ('550e8400-e29b-41d4-a716-446655440001', 'test@example.com', crypt('password123', gen_salt('bf')), now(), now(), now());

-- The user profile will be created automatically via the trigger

-- Sample chat sessions (uncomment after creating a test user)
-- INSERT INTO public.chat_sessions (user_id, title)
-- VALUES 
--   ('550e8400-e29b-41d4-a716-446655440001', 'First conversation about the app'),
--   ('550e8400-e29b-41d4-a716-446655440001', 'Questions about mental models');

-- Sample messages (uncomment after creating sessions)
-- INSERT INTO public.chat_messages (session_id, role, content)
-- VALUES 
--   ((SELECT id FROM public.chat_sessions LIMIT 1), 'user', 'Hello, I want to learn about mental models'),
--   ((SELECT id FROM public.chat_sessions LIMIT 1), 'assistant', 'I''d be happy to help you understand mental models. Mental models are simplified representations of how something works...');