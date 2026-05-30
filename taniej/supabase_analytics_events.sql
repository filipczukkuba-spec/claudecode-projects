-- Lightweight self-hosted events table.
-- Captures custom events (search_submitted, receipt_scanned, etc.) without
-- needing a paid analytics plan. Run ONCE in Supabase SQL Editor.

CREATE TABLE IF NOT EXISTS analytics_events (
  id           BIGSERIAL PRIMARY KEY,
  event        TEXT NOT NULL,
  properties   JSONB,
  session_id   TEXT,                                    -- anon UUID kept in localStorage
  ip_hash      TEXT,                                    -- sha256 prefix, for unique-visitor counts
  user_agent   TEXT,
  referrer     TEXT,
  path         TEXT,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_events_event_time   ON analytics_events(event, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_events_time         ON analytics_events(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_events_session      ON analytics_events(session_id, created_at DESC);

-- RLS: anyone can INSERT (so the public app can write), only service role reads.
ALTER TABLE analytics_events ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename = 'analytics_events' AND policyname = 'events_insert'
  ) THEN
    CREATE POLICY "events_insert" ON analytics_events FOR INSERT WITH CHECK (true);
  END IF;
END $$;

-- Verification
SELECT 'analytics_events ready' AS status;
