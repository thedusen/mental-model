-- Fix questionnaire triggers and function issues

-- First, create the missing update_updated_at_column function
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    return NEW;
END;
$$ language 'plpgsql';

-- Re-create the triggers if they don't exist
DROP TRIGGER IF EXISTS update_questionnaire_responses_updated_at ON public.user_questionnaire_responses;
CREATE TRIGGER update_questionnaire_responses_updated_at
  BEFORE UPDATE ON public.user_questionnaire_responses
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_questionnaire_progress_updated_at ON public.user_questionnaire_progress;
CREATE TRIGGER update_questionnaire_progress_updated_at
  BEFORE UPDATE ON public.user_questionnaire_progress
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();