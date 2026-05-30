-- Receipt scanner schema
-- Run ONCE in Supabase SQL Editor

-- 1. Track each scan attempt (for analytics + abuse prevention)
CREATE TABLE IF NOT EXISTS receipt_scans (
  id              BIGSERIAL PRIMARY KEY,
  store_id        BIGINT REFERENCES stores(id) ON DELETE SET NULL,
  receipt_date    DATE,
  receipt_total   DECIMAL(10,2),
  extracted_total DECIMAL(10,2),
  item_count      INTEGER DEFAULT 0,
  status          TEXT NOT NULL DEFAULT 'pending',  -- pending | ok | rejected
  reject_reason   TEXT,
  city            TEXT,
  ip_hash         TEXT,                             -- crude rate-limit key
  scanned_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_receipt_scans_status     ON receipt_scans(status);
CREATE INDEX IF NOT EXISTS idx_receipt_scans_scanned    ON receipt_scans(scanned_at DESC);
CREATE INDEX IF NOT EXISTS idx_receipt_scans_ip         ON receipt_scans(ip_hash, scanned_at DESC);

ALTER TABLE receipt_scans ENABLE ROW LEVEL SECURITY;
DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename = 'receipt_scans' AND policyname = 'receipt_scans_read'
  ) THEN
    CREATE POLICY "receipt_scans_read" ON receipt_scans FOR SELECT USING (true);
  END IF;
END $$;

-- 2. Tag price_reports with their provenance so we can distinguish
--    manual entries from receipt extractions.
ALTER TABLE price_reports
  ADD COLUMN IF NOT EXISTS source TEXT DEFAULT 'manual',
  ADD COLUMN IF NOT EXISTS scan_id BIGINT REFERENCES receipt_scans(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS is_promo BOOLEAN DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_price_reports_scan ON price_reports(scan_id);

-- 3. Verification
SELECT 'receipt_scans created'         AS status, COUNT(*) AS rows FROM receipt_scans;
SELECT 'price_reports has source col'  AS status FROM information_schema.columns
  WHERE table_name = 'price_reports' AND column_name = 'source';
