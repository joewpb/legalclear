-- User profiles for LegalClear — enables attorney referral and case tracking.
CREATE TABLE IF NOT EXISTS user_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT,
    full_name TEXT,
    phone TEXT,
    case_category TEXT,
    case_summary TEXT,
    urgency TEXT DEFAULT 'standard',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_up_email ON user_profiles (email);

-- Attorney referral inquiries — AI intake conversations submitted for review.
CREATE TABLE IF NOT EXISTS attorney_inquiries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES user_profiles(id) ON DELETE CASCADE,
    conversation JSONB NOT NULL DEFAULT '[]',
    intake_summary TEXT,
    recommended_attorney TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT now(),
    reviewed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_ai_user ON attorney_inquiries (user_id);
CREATE INDEX IF NOT EXISTS idx_ai_status ON attorney_inquiries (status);
