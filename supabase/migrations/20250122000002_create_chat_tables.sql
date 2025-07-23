-- Chat sessions table
CREATE TABLE IF NOT EXISTS public.chat_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES public.user_profiles(id) ON DELETE CASCADE,
  title TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  metadata JSONB DEFAULT '{}',
  
  -- For future Zep integration
  zep_session_id TEXT UNIQUE,
  zep_user_id TEXT
);

-- Chat messages table
CREATE TABLE IF NOT EXISTS public.chat_messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID REFERENCES public.chat_sessions(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
  content TEXT NOT NULL,
  timestamp TIMESTAMPTZ DEFAULT NOW(),
  metadata JSONB DEFAULT '{}',
  
  -- For future Zep integration and search
  zep_message_id TEXT,
  search_vector tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED
);

-- Indexes for performance
CREATE INDEX idx_chat_sessions_user_id ON public.chat_sessions(user_id);
CREATE INDEX idx_chat_sessions_updated_at ON public.chat_sessions(updated_at DESC);
CREATE INDEX idx_chat_messages_session_id ON public.chat_messages(session_id);
CREATE INDEX idx_chat_messages_timestamp ON public.chat_messages(timestamp DESC);
CREATE INDEX idx_chat_messages_search ON public.chat_messages USING gin(search_vector);

-- Enable Row Level Security
ALTER TABLE public.chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chat_messages ENABLE ROW LEVEL SECURITY;

-- RLS Policies for chat_sessions
CREATE POLICY "Users can view own sessions" ON public.chat_sessions
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own sessions" ON public.chat_sessions
  FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own sessions" ON public.chat_sessions
  FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own sessions" ON public.chat_sessions
  FOR DELETE USING (auth.uid() = user_id);

-- RLS Policies for chat_messages
CREATE POLICY "Users can view own messages" ON public.chat_messages
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM public.chat_sessions 
      WHERE id = chat_messages.session_id AND user_id = auth.uid()
    )
  );

CREATE POLICY "Users can insert own messages" ON public.chat_messages
  FOR INSERT WITH CHECK (
    EXISTS (
      SELECT 1 FROM public.chat_sessions 
      WHERE id = chat_messages.session_id AND user_id = auth.uid()
    )
  );

CREATE POLICY "Users can update own messages" ON public.chat_messages
  FOR UPDATE USING (
    EXISTS (
      SELECT 1 FROM public.chat_sessions 
      WHERE id = chat_messages.session_id AND user_id = auth.uid()
    )
  );

CREATE POLICY "Users can delete own messages" ON public.chat_messages
  FOR DELETE USING (
    EXISTS (
      SELECT 1 FROM public.chat_sessions 
      WHERE id = chat_messages.session_id AND user_id = auth.uid()
    )
  );

-- Updated_at trigger for chat_sessions
CREATE TRIGGER update_chat_sessions_updated_at
  BEFORE UPDATE ON public.chat_sessions
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to generate session title from first message
CREATE OR REPLACE FUNCTION public.generate_session_title()
RETURNS TRIGGER AS $$
BEGIN
  -- Only generate title if this is the first user message and title is null
  IF NEW.role = 'user' AND NOT EXISTS (
    SELECT 1 FROM public.chat_messages 
    WHERE session_id = NEW.session_id AND role = 'user' AND id != NEW.id
  ) THEN
    UPDATE public.chat_sessions
    SET title = CASE 
      WHEN LENGTH(NEW.content) > 50 THEN LEFT(NEW.content, 47) || '...'
      ELSE NEW.content
    END
    WHERE id = NEW.session_id AND title IS NULL;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-generate session title
CREATE TRIGGER auto_generate_session_title
  AFTER INSERT ON public.chat_messages
  FOR EACH ROW EXECUTE FUNCTION public.generate_session_title();