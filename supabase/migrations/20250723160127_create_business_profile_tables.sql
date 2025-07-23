-- Create business profile questionnaire tables
-- This migration adds support for collecting and storing business profile information

-- User business profile responses table
CREATE TABLE IF NOT EXISTS public.user_business_profiles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES public.user_profiles(id) ON DELETE CASCADE NOT NULL,
  question_id INTEGER NOT NULL,
  question_text TEXT NOT NULL,
  answer TEXT,
  answer_type VARCHAR(50) NOT NULL DEFAULT 'text', -- 'text', 'select', 'scale', 'number'
  answered_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  
  -- Progress tracking
  session_id UUID REFERENCES public.chat_sessions(id) ON DELETE SET NULL,
  is_complete BOOLEAN DEFAULT FALSE NOT NULL,
  
  -- Zep integration tracking
  synced_to_zep BOOLEAN DEFAULT FALSE NOT NULL,
  zep_sync_at TIMESTAMPTZ,
  
  -- Ensure one answer per user per question
  UNIQUE(user_id, question_id)
);

-- User questionnaire progress tracking table
CREATE TABLE IF NOT EXISTS public.user_questionnaire_progress (
  user_id UUID PRIMARY KEY REFERENCES public.user_profiles(id) ON DELETE CASCADE,
  questions_completed INTEGER DEFAULT 0 NOT NULL,
  total_questions INTEGER DEFAULT 11 NOT NULL,
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  last_question_at TIMESTAMPTZ,
  current_question_id INTEGER,
  
  -- Nudging data for UX optimization
  nudge_count INTEGER DEFAULT 0 NOT NULL,
  last_nudged_at TIMESTAMPTZ,
  nudge_dismissed_count INTEGER DEFAULT 0 NOT NULL,
  
  created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Indexes for performance
CREATE INDEX idx_user_business_profiles_user_id ON public.user_business_profiles(user_id);
CREATE INDEX idx_user_business_profiles_question_id ON public.user_business_profiles(question_id);
CREATE INDEX idx_user_business_profiles_answered_at ON public.user_business_profiles(answered_at DESC);
CREATE INDEX idx_user_business_profiles_session_id ON public.user_business_profiles(session_id);
CREATE INDEX idx_user_business_profiles_sync_status ON public.user_business_profiles(synced_to_zep, zep_sync_at);

-- Enable Row Level Security
ALTER TABLE public.user_business_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_questionnaire_progress ENABLE ROW LEVEL SECURITY;

-- RLS Policies for user_business_profiles
CREATE POLICY "Users can view own business profile data" ON public.user_business_profiles
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own business profile data" ON public.user_business_profiles
  FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own business profile data" ON public.user_business_profiles
  FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own business profile data" ON public.user_business_profiles
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

-- Updated_at triggers
CREATE TRIGGER update_user_business_profiles_updated_at
  BEFORE UPDATE ON public.user_business_profiles
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_questionnaire_progress_updated_at
  BEFORE UPDATE ON public.user_questionnaire_progress
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to update questionnaire progress when profile answers are inserted/updated
CREATE OR REPLACE FUNCTION public.update_questionnaire_progress()
RETURNS TRIGGER AS $$
BEGIN
  -- Insert or update progress record
  INSERT INTO public.user_questionnaire_progress (
    user_id,
    questions_completed,
    started_at,
    last_question_at,
    current_question_id
  )
  VALUES (
    NEW.user_id,
    1,
    COALESCE(NEW.answered_at, NOW()),
    COALESCE(NEW.answered_at, NOW()),
    NEW.question_id
  )
  ON CONFLICT (user_id) DO UPDATE SET
    questions_completed = (
      SELECT COUNT(*) 
      FROM public.user_business_profiles 
      WHERE user_id = NEW.user_id AND answered_at IS NOT NULL
    ),
    last_question_at = COALESCE(NEW.answered_at, NOW()),
    current_question_id = NEW.question_id,
    completed_at = CASE 
      WHEN (
        SELECT COUNT(*) 
        FROM public.user_business_profiles 
        WHERE user_id = NEW.user_id AND answered_at IS NOT NULL
      ) >= user_questionnaire_progress.total_questions 
      THEN COALESCE(NEW.answered_at, NOW())
      ELSE user_questionnaire_progress.completed_at
    END,
    updated_at = NOW();

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to automatically update progress
CREATE TRIGGER trigger_update_questionnaire_progress
  AFTER INSERT OR UPDATE ON public.user_business_profiles
  FOR EACH ROW 
  WHEN (NEW.answered_at IS NOT NULL)
  EXECUTE FUNCTION public.update_questionnaire_progress();

-- Insert default question structure (this will be used by the frontend)
-- We'll store the questions as reference data for consistency
CREATE TABLE IF NOT EXISTS public.business_profile_questions (
  id INTEGER PRIMARY KEY,
  question_text TEXT NOT NULL,
  answer_type VARCHAR(50) NOT NULL DEFAULT 'text',
  options JSONB, -- For select type questions
  order_index INTEGER NOT NULL,
  is_active BOOLEAN DEFAULT TRUE NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Insert the 11 business profile questions
INSERT INTO public.business_profile_questions (id, question_text, answer_type, options, order_index) VALUES
(1, 'What''s the biggest challenge slowing your business growth right now?', 'text', NULL, 1),
(2, 'How many employees work in your business?', 'select', '["Just me", "2-5 employees", "6-10 employees", "11-25 employees", "26-50 employees", "51-100 employees", "100+ employees"]', 2),
(3, 'What''s your approximate annual revenue range?', 'select', '["Under $100K", "$100K-$500K", "$500K-$1M", "$1M-$5M", "$5M+", "Prefer not to say"]', 3),
(4, 'What industry best describes your business?', 'select', '["Technology/Software", "Professional Services", "Retail/E-commerce", "Healthcare", "Manufacturing", "Real Estate", "Financial Services", "Education", "Marketing/Advertising", "Construction", "Food & Beverage", "Other"]', 4),
(5, 'How do you typically measure business success?', 'select', '["Revenue growth", "Profit margins", "Customer satisfaction", "Market share", "Employee satisfaction", "Cash flow", "Number of customers", "Other"]', 5),
(6, 'On a typical day, how similar is your work to your team''s work?', 'scale', '{"min": 1, "max": 5, "labels": ["Completely different", "Mostly different", "Mixed", "Mostly similar", "Nearly identical"]}', 6),
(7, 'What''s your most important business goal for the next 1-3 years?', 'text', NULL, 7),
(8, 'How does your business operate when you''re away for a day?', 'select', '["Runs smoothly without me", "Some minor issues but manageable", "Several issues arise", "Significant problems occur", "Cannot function without me"]', 8),
(9, 'How many critical decisions can only you make?', 'select', '["Almost all decisions", "Most decisions", "About half", "Some decisions", "Very few decisions"]', 9),
(10, 'Do you have enough team members to double your business size?', 'select', '["Definitely yes", "Probably yes", "Not sure", "Probably no", "Definitely no"]', 10),
(11, 'How confident are you in your business''s profitability over the next 6 months?', 'scale', '{"min": 1, "max": 5, "labels": ["Not confident", "Slightly confident", "Moderately confident", "Very confident", "Extremely confident"]}', 11)
ON CONFLICT (id) DO NOTHING;

-- Enable RLS on questions table (read-only for users)
ALTER TABLE public.business_profile_questions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Anyone can view business profile questions" ON public.business_profile_questions
  FOR SELECT USING (TRUE);