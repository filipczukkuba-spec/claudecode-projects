-- Schema additions for the scraper system
-- Run ONCE in Supabase SQL Editor

-- Add source + timestamp tracking to prices table
ALTER TABLE prices ADD COLUMN IF NOT EXISTS source TEXT DEFAULT 'estimated';
ALTER TABLE prices ADD COLUMN IF NOT EXISTS scraped_at TIMESTAMPTZ;

-- Mark existing prices as estimated (they were seeded via SQL, not scraped)
UPDATE prices SET source = 'estimated' WHERE source IS NULL;

-- Price history: every scraped update is logged here
CREATE TABLE IF NOT EXISTS price_history (
  id          BIGSERIAL PRIMARY KEY,
  product_id  BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  store_id    BIGINT NOT NULL REFERENCES stores(id)   ON DELETE CASCADE,
  price       DECIMAL(10,2) NOT NULL,
  source      TEXT NOT NULL DEFAULT 'scraped',
  recorded_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ph_product_store ON price_history(product_id, store_id);
CREATE INDEX IF NOT EXISTS idx_ph_recorded      ON price_history(recorded_at DESC);

-- RLS: public read, only service role can insert
ALTER TABLE price_history ENABLE ROW LEVEL SECURITY;
DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename = 'price_history' AND policyname = 'price_history_read'
  ) THEN
    CREATE POLICY "price_history_read" ON price_history FOR SELECT USING (true);
  END IF;
END $$;

-- Verification
SELECT
  (SELECT COUNT(*) FROM prices WHERE source = 'scraped')   AS scraped_prices,
  (SELECT COUNT(*) FROM prices WHERE source = 'estimated') AS estimated_prices,
  (SELECT COUNT(*) FROM price_history)                     AS history_rows;
