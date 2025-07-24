-- Chat-Integrated Questionnaire Tables Migration
-- This migration creates the new questionnaire system for chat-based business profile collection

-- Drop existing business profile tables to start fresh with new design
DROP TABLE IF EXISTS public.user_business_profiles CASCADE;
DROP TABLE IF EXISTS public.user_questionnaire_progress CASCADE;
DROP TABLE IF EXISTS public.business_profile_questions CASCADE;
DROP FUNCTION IF EXISTS public.update_questionnaire_progress() CASCADE;

-- Store the 11 predefined questions
CREATE TABLE public.questionnaire_questions (
  id SERIAL PRIMARY KEY,
  question_number INTEGER UNIQUE NOT NULL,
  question_text TEXT NOT NULL,
  question_category VARCHAR(50),
  created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Store user responses with proper foreign key relationships
CREATE TABLE public.user_questionnaire_responses (
  id SERIAL PRIMARY KEY,
  user_id UUID REFERENCES public.user_profiles(id) ON DELETE CASCADE NOT NULL,
  question_id INTEGER REFERENCES public.questionnaire_questions(id) ON DELETE CASCADE NOT NULL,
  response_text TEXT,
  skipped BOOLEAN DEFAULT FALSE NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  
  -- Ensure one response per user per question
  UNIQUE(user_id, question_id)
);

-- Track questionnaire progress per user
CREATE TABLE public.user_questionnaire_progress (
  user_id UUID PRIMARY KEY REFERENCES public.user_profiles(id) ON DELETE CASCADE,
  current_question INTEGER NOT NULL DEFAULT 1,
  status VARCHAR(20) NOT NULL DEFAULT 'not_started' CHECK (status IN ('not_started', 'in_progress', 'paused', 'completed')),
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  last_updated TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Insert the 11 business profile questions
INSERT INTO public.questionnaire_questions (question_number, question_text, question_category) VALUES
(1, 'What industry is your business in?', 'business_context'),
(2, 'What is the size of your company (number of employees)?', 'business_context'),
(3, 'What is your role in the company?', 'personal_context'),
(4, 'What are your primary business goals for the next 12 months?', 'goals'),
(5, 'What are the biggest challenges your business currently faces?', 'challenges'),
(6, 'Who is your target customer or market?', 'market'),
(7, 'What products or services does your business offer?', 'offerings'),
(8, 'What is your current revenue model?', 'financial'),
(9, 'What key metrics do you track to measure success?', 'metrics'),
(10, 'What is your competitive advantage?', 'strategy'),
(11, 'What additional context would help me better understand your business?', 'context');

-- Create indexes for performance
CREATE INDEX idx_questionnaire_responses_user_id ON public.user_questionnaire_responses(user_id);
CREATE INDEX idx_questionnaire_responses_question_id ON public.user_questionnaire_responses(question_id);
CREATE INDEX idx_questionnaire_responses_created_at ON public.user_questionnaire_responses(created_at DESC);
CREATE INDEX idx_questionnaire_progress_status ON public.user_questionnaire_progress(status);
CREATE INDEX idx_questionnaire_progress_updated ON public.user_questionnaire_progress(last_updated DESC);

-- Enable Row Level Security
ALTER TABLE public.questionnaire_questions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_questionnaire_responses ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_questionnaire_progress ENABLE ROW LEVEL SECURITY;

-- RLS Policies for questionnaire_questions (read-only for all authenticated users)
CREATE POLICY "Authenticated users can view questionnaire questions" ON public.questionnaire_questions
  FOR SELECT USING (auth.role() = 'authenticated');

-- RLS Policies for user_questionnaire_responses
CREATE POLICY "Users can view own questionnaire responses" ON public.user_questionnaire_responses
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own questionnaire responses" ON public.user_questionnaire_responses
  FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own questionnaire responses" ON public.user_questionnaire_responses
  FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own questionnaire responses" ON public.user_questionnaire_responses
  FOR DELETE USING (auth.uid() = user_id);

-- RLS Policies for user_questionnaire_progress
CREATE POLICY "Users can view own questionnaire progress" ON public.user_questionnaire_progress
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own questionnaire progress" ON public.user_questionnaire_progress
  FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own questionnaire progress" ON public.user_questionnaire_progress
  FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own questionnaire progress" ON public.user_questionnaire_progress
  FOR DELETE USING (auth.uid() = user_id);

-- Updated_at trigger for responses table
CREATE TRIGGER update_questionnaire_responses_updated_at
  BEFORE UPDATE ON public.user_questionnaire_responses
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Updated_at trigger for progress table
CREATE TRIGGER update_questionnaire_progress_updated_at
  BEFORE UPDATE ON public.user_questionnaire_progress
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to automatically update progress when responses are added/updated
CREATE OR REPLACE FUNCTION public.update_questionnaire_progress_on_response()
RETURNS TRIGGER AS $$
DECLARE
  answered_count INTEGER;
  total_questions INTEGER := 11;
BEGIN
  -- Count answered questions for this user
  SELECT COUNT(*) INTO answered_count
  FROM public.user_questionnaire_responses 
  WHERE user_id = NEW.user_id AND response_text IS NOT NULL AND response_text != '';

  -- Update or insert progress record
  INSERT INTO public.user_questionnaire_progress (
    user_id,
    current_question,
    status,
    started_at,
    last_updated
  )
  VALUES (
    NEW.user_id,
    NEW.question_id + 1, -- Next question
    CASE 
      WHEN answered_count >= total_questions THEN 'completed'
      ELSE 'in_progress'
    END,
    NOW(),
    NOW()
  )
  ON CONFLICT (user_id) DO UPDATE SET
    current_question = CASE 
      WHEN EXCLUDED.status = 'completed' THEN user_questionnaire_progress.current_question
      ELSE NEW.question_id + 1
    END,
    status = CASE 
      WHEN answered_count >= total_questions THEN 'completed'
      WHEN user_questionnaire_progress.status = 'not_started' THEN 'in_progress'
      ELSE user_questionnaire_progress.status
    END,
    completed_at = CASE 
      WHEN answered_count >= total_questions THEN NOW()
      ELSE user_questionnaire_progress.completed_at
    END,
    last_updated = NOW();

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to automatically update progress when responses change
CREATE TRIGGER trigger_update_questionnaire_progress_on_response
  AFTER INSERT OR UPDATE ON public.user_questionnaire_responses
  FOR EACH ROW 
  EXECUTE FUNCTION public.update_questionnaire_progress_on_response();

-- Grant necessary permissions
GRANT SELECT ON public.questionnaire_questions TO authenticated;
GRANT ALL ON public.user_questionnaire_responses TO authenticated;
GRANT ALL ON public.user_questionnaire_progress TO authenticated;
GRANT USAGE ON SEQUENCE public.questionnaire_questions_id_seq TO authenticated;
GRANT USAGE ON SEQUENCE public.user_questionnaire_responses_id_seq TO authenticated;