-- Drop the problematic updated_at triggers
-- The update_updated_at_column function is trying to set updated_at field that doesn't exist

DROP TRIGGER IF EXISTS update_questionnaire_responses_updated_at ON public.user_questionnaire_responses;
DROP TRIGGER IF EXISTS update_questionnaire_progress_updated_at ON public.user_questionnaire_progress;

-- Keep the function but don't use it on these tables for now
-- The tables already have updated_at columns with DEFAULT NOW() which is sufficient